import time
import logging
import os
import shutil

from django.core.management.base import BaseCommand
from chatbot.models import TradeData
from chatbot.services.scraper import run_scraper, setup_driver, get_matching_countries
from chatbot.services.storage import upload_file_to_supabase
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Continuously polls DB for pending scrape jobs and runs them"

    def handle(self, *args, **options):
        self.stdout.write("🚀 Scraper worker started. Polling for jobs...")

        while True:
            try:
                # Find oldest processing job
                job = TradeData.objects.filter(
                    status="processing"
                ).order_by("created_at").first()

                if not job:
                    time.sleep(5)
                    continue

                self.stdout.write(f"📋 Found job: {job.country} {job.data_type} {job.year}")

                # Skip if already has a file (completed by another process)
                job.refresh_from_db()
                if job.status != "processing":
                    continue

                self._process_job(job)

            except Exception as e:
                logger.error(f"Worker loop error: {e}", exc_info=True)
                time.sleep(10)

    def _process_job(self, job):
        try:
            # Step 1: Find exact country name on website
            driver = None
            exact_country = job.country
            try:
                driver = setup_driver()
                matches = get_matching_countries(
                    driver, job.country,
                    is_import=(job.data_type == "import")
                )
                if matches:
                    exact_country = matches[0]
                    self.stdout.write(f"✅ Exact country: {exact_country}")
                else:
                    raise Exception(f"Country '{job.country}' not found on trade portal")
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass

            # Update country name to exact match
            job.country = exact_country
            job.save()

            # Step 2: Scrape
            self.stdout.write(f"🔍 Scraping: {exact_country} {job.data_type} {job.year}")
            file_path = run_scraper(job.data_type, exact_country, job.year)

            # Step 3: Upload to Supabase
            try:
                stored_path = upload_file_to_supabase(file_path)
                self.stdout.write(f"☁️ Uploaded: {stored_path}")
            except Exception as upload_err:
                self.stdout.write(f"⚠️ Supabase failed, using local: {upload_err}")
                media_root = str(settings.MEDIA_ROOT)
                os.makedirs(media_root, exist_ok=True)
                dest = os.path.join(media_root, os.path.basename(file_path))
                if os.path.abspath(file_path) != os.path.abspath(dest):
                    shutil.move(file_path, dest)
                stored_path = dest

            # Step 4: Mark completed
            job.refresh_from_db()
            job.file = stored_path
            job.status = "completed"
            job.save()
            self.stdout.write(f"✅ Job done: {stored_path}")

        except Exception as e:
            self.stdout.write(f"❌ Job failed: {e}")
            logger.error(f"Job failed for {job.id}: {e}", exc_info=True)
            try:
                job.refresh_from_db()
                job.status = "failed"
                job.error_message = str(e)
                job.save()
            except Exception:
                pass