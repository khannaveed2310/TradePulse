# import os
# import json
# import logging
# import threading
# import re
# import shutil

# from django.conf import settings
# from django.views.decorators.csrf import csrf_exempt
# from rest_framework.decorators import api_view
# from rest_framework.response import Response
# from rest_framework import status

# from .models import TradeData
# from .services.scraper import run_scraper, get_matching_countries, setup_driver
# from .services.storage import upload_file_to_supabase

# logger = logging.getLogger(__name__)
# ongoing_scrapes = {}


# def build_file_url(file_path_or_url):
#     if not file_path_or_url:
#         return None
#     if file_path_or_url.startswith("http"):
#         return file_path_or_url
#     media_root = str(settings.MEDIA_ROOT)
#     if file_path_or_url.startswith(media_root):
#         rel = file_path_or_url[len(media_root):].lstrip("/\\")
#         return f"{settings.MEDIA_URL}{rel}"
#     return file_path_or_url


# def parse_message(message):
#     """
#     Extract data_type, country keyword, user_year from message.
#     user_year is stored AS-IS (e.g. "2025") — no conversion needed.
#     The scraper matches year by checking if user_year is IN the option text.
#     """
#     msg_lower = message.lower()
#     data_type = "import" if "import" in msg_lower else "export"

#     year_match = re.search(r"\b(20\d{2})\b", msg_lower)
#     user_year = year_match.group(1) if year_match else None

#     skip_words = {
#         "show", "me", "i", "need", "want", "get", "fetch", "find",
#         "import", "export", "data", "for", "of", "in", "the", "from",
#         "trade", "year", "please", "give",
#     }
#     words = re.sub(r"[^\w\s]", "", msg_lower).split()
#     country_words = [w for w in words if w not in skip_words and not w.isdigit()]
#     country_keyword = " ".join(country_words).strip()

#     return data_type, country_keyword, user_year


# def search_db(country_keyword, user_year, data_type):
#     """Search DB by partial country name and year."""
#     if not country_keyword or not user_year:
#         return []
#     first_word = country_keyword.split()[0]
#     return list(
#         TradeData.objects.filter(
#             country__icontains=first_word,
#             year=user_year,
#             data_type=data_type,
#         ).order_by("-created_at")
#     )


# def scrape_and_save(data_type, country, user_year, trade_data_id):
#     key = f"{country}_{user_year}_{data_type}"
#     try:
#         logger.info(f"[BG] Scraping: {country} {data_type} {user_year}")
#         file_path = run_scraper(data_type, country, user_year)

#         try:
#             stored_path = upload_file_to_supabase(file_path)
#             logger.info(f"[BG] Uploaded to Supabase: {stored_path}")
#         except Exception as upload_err:
#             logger.warning(f"[BG] Supabase failed, using local: {upload_err}")
#             media_root = str(settings.MEDIA_ROOT)
#             os.makedirs(media_root, exist_ok=True)
#             dest = os.path.join(media_root, os.path.basename(file_path))
#             if os.path.abspath(file_path) != os.path.abspath(dest):
#                 shutil.move(file_path, dest)
#             stored_path = dest

#         trade_data = TradeData.objects.get(id=trade_data_id)
#         trade_data.file = stored_path
#         trade_data.status = "completed"
#         trade_data.save()
#         logger.info(f"[BG] Done: {stored_path}")

#     except Exception as e:
#         logger.error(f"[BG] Failed: {e}", exc_info=True)
#         try:
#             trade_data = TradeData.objects.get(id=trade_data_id)
#             trade_data.status = "failed"
#             trade_data.error_message = str(e)
#             trade_data.save()
#         except Exception:
#             pass
#     finally:
#         ongoing_scrapes.pop(key, None)


# @api_view(["POST"])
# @csrf_exempt
# def chat(request):
#     try:
#         body = json.loads(request.body)
#         message = body.get("message", "").strip()
#         selected_country = body.get("selected_country", "").strip()

#         if not message:
#             return Response({"message": "Please type something.", "source": "error"}, status=400)

#         logger.info(f"Chat — message: {message!r} | selected: {selected_country!r}")

#         data_type, country_keyword, user_year = parse_message(message)

#         # ── User selected a country from options ───────────────────────────
#         if selected_country:
#             if not user_year:
#                 return Response({"message": "Please include a year (e.g. 2025).", "source": "error"})
#             return _handle_trade_request(data_type, selected_country, user_year)

#         # ── No trade keyword → pure country search on website ──────────────
#         has_trade_keyword = any(
#             kw in message.lower()
#             for kw in ["import", "export", "show", "get", "fetch", "give", "need"]
#         )
#         if not has_trade_keyword:
#             return _website_country_search(message)

#         # ── Validate ───────────────────────────────────────────────────────
#         if not user_year:
#             return Response({"message": "Please include a year (e.g. 2025).", "source": "error"})
#         if not country_keyword:
#             return Response({"message": "Please mention a country.", "source": "error"})

#         # ── STEP 1: Search DB first ────────────────────────────────────────
#         db_results = search_db(country_keyword, user_year, data_type)
#         completed  = [r for r in db_results if r.status == "completed" and r.file]
#         processing = [r for r in db_results if r.status == "processing"]

#         # One completed → return download immediately
#         if len(completed) == 1:
#             record = completed[0]
#             return Response({
#                 "message": f"✅ Found in database! {data_type.capitalize()} data for {record.country} ({user_year}).",
#                 "file_url": build_file_url(record.file),
#                 "source": "db",
#             })

#         # Multiple completed → ask user to pick
#         if len(completed) > 1:
#             return Response({
#                 "message": f"Multiple records found for '{country_keyword}' ({user_year}). Please select one:",
#                 "options": [r.country for r in completed],
#                 "source": "options",
#             })

#         # Still processing → tell user to wait
#         if processing:
#             record = processing[0]
#             ongoing_scrapes[f"{record.country}_{user_year}_{data_type}"] = True
#             return Response({
#                 "message": f"⏳ Data for {record.country} {data_type} {user_year} is still being fetched. Please wait...",
#                 "source": "processing",
#             })

#         # ── STEP 2: Not in DB → look up on website then scrape ────────────
#         return _scrape_with_country_lookup(data_type, country_keyword, user_year)

#     except json.JSONDecodeError:
#         return Response({"message": "Invalid request format.", "source": "error"}, status=400)
#     except Exception as e:
#         logger.error(f"Error in chat: {e}", exc_info=True)
#         return Response({"message": f"Server error: {str(e)}", "source": "error"}, status=500)


# def _website_country_search(search_text):
#     driver = None
#     try:
#         driver = setup_driver()
#         matches = get_matching_countries(driver, search_text, is_import=False)
#         if matches:
#             return Response({
#                 "message": f"Found {len(matches)} countries matching '{search_text}'. Please refine with 'import'/'export' and a year.",
#                 "options": matches[:10],
#                 "source": "options",
#             })
#         return Response({"message": f"No countries found matching '{search_text}'.", "source": "error"})
#     except Exception as e:
#         return Response({"message": f"Error: {str(e)}", "source": "error"})
#     finally:
#         if driver:
#             try:
#                 driver.quit()
#             except Exception:
#                 pass


# def _scrape_with_country_lookup(data_type, country_keyword, user_year):
#     """
#     Search the website dropdown for country_keyword.
#     0 results → error
#     1 result  → start scraping immediately
#     2+ results → return options for user to pick
#     """
#     driver = None
#     try:
#         driver = setup_driver()
#         matches = get_matching_countries(driver, country_keyword, is_import=(data_type == "import"))
#     except Exception as e:
#         logger.error(f"Country lookup error: {e}")
#         matches = []
#     finally:
#         if driver:
#             try:
#                 driver.quit()
#             except Exception:
#                 pass

#     if not matches:
#         return Response({
#             "message": f"Could not find '{country_keyword}' on the trade portal. Please check the spelling.",
#             "source": "error",
#         })

#     if len(matches) == 1:
#         # Only one match → scrape directly
#         return _handle_trade_request(data_type, matches[0], user_year)

#     # Multiple matches → ask user
#     return Response({
#         "message": f"Multiple countries found for '{country_keyword}'. Please select one:",
#         "options": matches[:10],
#         "source": "options",
#     })


# def _handle_trade_request(data_type, country, user_year):
#     """
#     Check DB one final time with exact name, then start scrape if needed.
#     """
#     existing = TradeData.objects.filter(
#         country__iexact=country,
#         year=user_year,
#         data_type=data_type,
#     ).order_by("-created_at").first()

#     if existing:
#         if existing.status == "completed" and existing.file:
#             return Response({
#                 "message": f"✅ Found in database! {data_type.capitalize()} data for {existing.country} ({user_year}).",
#                 "file_url": build_file_url(existing.file),
#                 "source": "db",
#             })
#         elif existing.status == "processing":
#             ongoing_scrapes[f"{existing.country}_{user_year}_{data_type}"] = True
#             return Response({
#                 "message": f"⏳ Already fetching {existing.country} {data_type} {user_year}... Please wait.",
#                 "source": "processing",
#             })
#         elif existing.status == "failed":
#             existing.delete()

#     # Create record and start background scrape
#     trade_data = TradeData.objects.create(
#         country=country,
#         year=user_year,
#         data_type=data_type,
#         status="processing",
#     )
#     key = f"{country}_{user_year}_{data_type}"
#     ongoing_scrapes[key] = True

#     thread = threading.Thread(
#         target=scrape_and_save,
#         args=(data_type, country, user_year, trade_data.id),
#         daemon=True,
#     )
#     thread.start()

#     return Response({
#         "message": f"🔍 Fetching {data_type} data for {country} ({user_year})... This may take a minute.",
#         "source": "processing",
#     })


# @api_view(["GET"])
# def check_status(request):
#     """
#     GET /api/status/?country=Saudi&year=2025&data_type=export
#     Polls until source becomes 'db' or 'failed'.
#     """
#     country  = request.GET.get("country", "").strip()
#     user_year = request.GET.get("year", "").strip()
#     data_type = request.GET.get("data_type", "").strip()

#     if not (country and user_year and data_type):
#         return Response({"message": "Missing params.", "source": "error"}, status=400)

#     # Search by partial name (icontains on first word)
#     first_word = country.split()[0]
#     trade_data = TradeData.objects.filter(
#         country__icontains=first_word,
#         year=user_year,
#         data_type=data_type,
#     ).order_by("-created_at").first()

#     if not trade_data:
#         return Response({"message": "Record not found.", "source": "not_found"})

#     if trade_data.status == "completed" and trade_data.file:
#         return Response({
#             "message": f"✅ {data_type.capitalize()} data for {trade_data.country} ({user_year}) is ready!",
#             "file_url": build_file_url(trade_data.file),
#             "source": "db",
#         })

#     if trade_data.status == "processing":
#         return Response({"message": "⏳ Still processing, please wait...", "source": "processing"})

#     return Response({
#         "message": f"❌ Scraping failed: {trade_data.error_message or 'Unknown error'}",
#         "source": "failed",
#     })




























import os
import json
import logging
import threading
import re
import shutil

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import TradeData
from .services.scraper import run_scraper, get_matching_countries, setup_driver
from .services.storage import upload_file_to_supabase

logger = logging.getLogger(__name__)
ongoing_scrapes = {}


def build_file_url(file_path_or_url):
    if not file_path_or_url:
        return None
    if file_path_or_url.startswith("http"):
        return file_path_or_url
    media_root = str(settings.MEDIA_ROOT)
    if file_path_or_url.startswith(media_root):
        rel = file_path_or_url[len(media_root):].lstrip("/\\")
        return f"{settings.MEDIA_URL}{rel}"
    return file_path_or_url


def parse_message(message):
    msg_lower = message.lower()
    data_type = "import" if "import" in msg_lower else "export"
    year_match = re.search(r"\b(20\d{2})\b", msg_lower)
    user_year = year_match.group(1) if year_match else None
    skip_words = {
        "show", "me", "i", "need", "want", "get", "fetch", "find",
        "import", "export", "data", "for", "of", "in", "the", "from",
        "trade", "year", "please", "give",
    }
    words = re.sub(r"[^\w\s]", "", msg_lower).split()
    country_words = [w for w in words if w not in skip_words and not w.isdigit()]
    country_keyword = " ".join(country_words).strip()
    return data_type, country_keyword, user_year


def search_db(country_keyword, user_year, data_type):
    if not country_keyword or not user_year:
        return []
    first_word = country_keyword.split()[0]
    return list(
        TradeData.objects.filter(
            country__icontains=first_word,
            year=user_year,
            data_type=data_type,
        ).order_by("-created_at")
    )


def build_file_url(file_path_or_url):
    if not file_path_or_url:
        return None
    if file_path_or_url.startswith("http"):
        return file_path_or_url
    media_root = str(settings.MEDIA_ROOT)
    if file_path_or_url.startswith(media_root):
        rel = file_path_or_url[len(media_root):].lstrip("/\\")
        return f"{settings.MEDIA_URL}{rel}"
    return file_path_or_url


def scrape_and_save(data_type, country, user_year, trade_data_id):
    """Full background task — country lookup + scrape + upload."""
    key = f"{country}_{user_year}_{data_type}"
    try:
        logger.info(f"[BG] Starting: {country} {data_type} {user_year}")

        # Step 1: find exact country name on website
        driver = None
        exact_country = country
        try:
            driver = setup_driver()
            matches = get_matching_countries(driver, country, is_import=(data_type == "import"))
            if matches:
                exact_country = matches[0]
                logger.info(f"[BG] Exact country from site: {exact_country}")
            else:
                raise Exception(f"Country '{country}' not found on trade portal")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        # Update country name in DB to exact name
        trade_data = TradeData.objects.get(id=trade_data_id)
        trade_data.country = exact_country
        trade_data.save()

        # Step 2: scrape
        file_path = run_scraper(data_type, exact_country, user_year)

        # Step 3: upload
        try:
            stored_path = upload_file_to_supabase(file_path)
            logger.info(f"[BG] Uploaded: {stored_path}")
        except Exception as upload_err:
            logger.warning(f"[BG] Supabase failed, using local: {upload_err}")
            media_root = str(settings.MEDIA_ROOT)
            os.makedirs(media_root, exist_ok=True)
            dest = os.path.join(media_root, os.path.basename(file_path))
            if os.path.abspath(file_path) != os.path.abspath(dest):
                shutil.move(file_path, dest)
            stored_path = dest

        trade_data = TradeData.objects.get(id=trade_data_id)
        trade_data.file = stored_path
        trade_data.status = "completed"
        trade_data.save()
        logger.info(f"[BG] Done: {stored_path}")

    except Exception as e:
        logger.error(f"[BG] Failed: {e}", exc_info=True)
        try:
            trade_data = TradeData.objects.get(id=trade_data_id)
            trade_data.status = "failed"
            trade_data.error_message = str(e)
            trade_data.save()
        except Exception:
            pass
    finally:
        ongoing_scrapes.pop(key, None)


@api_view(["POST"])
@csrf_exempt
def chat(request):
    try:
        body = json.loads(request.body)
        message = body.get("message", "").strip()
        selected_country = body.get("selected_country", "").strip()

        if not message:
            return Response({"message": "Please type something.", "source": "error"}, status=400)

        logger.info(f"Chat — message: {message!r} | selected: {selected_country!r}")

        data_type, country_keyword, user_year = parse_message(message)

        # ── User selected a country from options ───────────────────────────
        if selected_country:
            if not user_year:
                return Response({"message": "Please include a year (e.g. 2025).", "source": "error"})
            return _handle_trade_request(data_type, selected_country, user_year)

        # ── No trade keyword → just tell user to be specific ──────────────
        has_trade_keyword = any(
            kw in message.lower()
            for kw in ["import", "export", "show", "get", "fetch", "give", "need"]
        )
        if not has_trade_keyword:
            return Response({
                "message": "Please specify 'import' or 'export', a country, and a year.\nExample: export data for Qatar 2025",
                "source": "error",
            })

        # ── Validate ───────────────────────────────────────────────────────
        if not user_year:
            return Response({"message": "Please include a year (e.g. 2025).", "source": "error"})
        if not country_keyword:
            return Response({"message": "Please mention a country.", "source": "error"})

        # ── STEP 1: Check DB first (fast — no Selenium) ────────────────────
        db_results = search_db(country_keyword, user_year, data_type)
        completed  = [r for r in db_results if r.status == "completed" and r.file]
        processing = [r for r in db_results if r.status == "processing"]

        # One completed → return download immediately
        if len(completed) == 1:
            record = completed[0]
            return Response({
                "message": f"✅ Found in database! {data_type.capitalize()} data for {record.country} ({user_year}).",
                "file_url": build_file_url(record.file),
                "source": "db",
            })

        # Multiple completed → ask user to pick
        if len(completed) > 1:
            return Response({
                "message": f"Multiple records found for '{country_keyword}'. Please select one:",
                "options": [r.country for r in completed],
                "source": "options",
            })

        # Already processing → tell user to wait
        if processing:
            record = processing[0]
            return Response({
                "message": f"⏳ Already fetching {record.country} {data_type} {user_year}. Please wait...",
                "source": "processing",
            })

        # ── STEP 2: Not in DB → start background task immediately ─────────
        # Don't run Selenium here — do it all in background to avoid 502
        return _start_background_scrape(data_type, country_keyword, user_year)

    except json.JSONDecodeError:
        return Response({"message": "Invalid request format.", "source": "error"}, status=400)
    except Exception as e:
        logger.error(f"Error in chat: {e}", exc_info=True)
        return Response({"message": f"Server error: {str(e)}", "source": "error"}, status=500)


def _start_background_scrape(data_type, country_keyword, user_year):
    """
    Immediately create a DB record and start background scrape.
    Returns 'processing' instantly — no Selenium in the request thread.
    """
    key = f"{country_keyword}_{user_year}_{data_type}"

    # Avoid duplicate tasks
    if key in ongoing_scrapes:
        return Response({
            "message": f"⏳ Already fetching {data_type} data for '{country_keyword}' ({user_year}). Please wait...",
            "source": "processing",
        })

    trade_data = TradeData.objects.create(
        country=country_keyword,
        year=user_year,
        data_type=data_type,
        status="processing",
    )
    ongoing_scrapes[key] = True

    thread = threading.Thread(
        target=scrape_and_save,
        args=(data_type, country_keyword, user_year, trade_data.id),
        daemon=True,
    )
    thread.start()

    return Response({
        "message": f"🔍 Fetching {data_type} data for '{country_keyword}' ({user_year})... This may take a minute.",
        "source": "processing",
    })


def _handle_trade_request(data_type, country, user_year):
    """Called when user selects a specific country from options."""
    existing = TradeData.objects.filter(
        country__iexact=country,
        year=user_year,
        data_type=data_type,
    ).order_by("-created_at").first()

    if existing:
        if existing.status == "completed" and existing.file:
            return Response({
                "message": f"✅ Found in database! {data_type.capitalize()} data for {existing.country} ({user_year}).",
                "file_url": build_file_url(existing.file),
                "source": "db",
            })
        elif existing.status == "processing":
            return Response({
                "message": f"⏳ Already fetching {existing.country} {data_type} {user_year}...",
                "source": "processing",
            })
        elif existing.status == "failed":
            existing.delete()

    return _start_background_scrape(data_type, country, user_year)


@api_view(["GET"])
def check_status(request):
    country   = request.GET.get("country", "").strip()
    user_year = request.GET.get("year", "").strip()
    data_type = request.GET.get("data_type", "").strip()

    if not (country and user_year and data_type):
        return Response({"message": "Missing params.", "source": "error"}, status=400)

    first_word = country.split()[0]
    trade_data = TradeData.objects.filter(
        country__icontains=first_word,
        year=user_year,
        data_type=data_type,
    ).order_by("-created_at").first()

    if not trade_data:
        return Response({"message": "Record not found.", "source": "not_found"})

    if trade_data.status == "completed" and trade_data.file:
        return Response({
            "message": f"✅ {data_type.capitalize()} data for {trade_data.country} ({user_year}) is ready!",
            "file_url": build_file_url(trade_data.file),
            "source": "db",
        })

    if trade_data.status == "processing":
        return Response({"message": "⏳ Still processing, please wait...", "source": "processing"})

    return Response({
        "message": f"❌ Scraping failed: {trade_data.error_message or 'Unknown error'}",
        "source": "failed",
    })