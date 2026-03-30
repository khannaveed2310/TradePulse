#!/usr/bin/env bash
set -e

echo "=== Installing system dependencies ==="
apt-get update -qq
apt-get install -y -qq \
    wget \
    curl \
    unzip \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    libgbm1 \
    libxss1 \
    libxtst6 \
    python3-dev \
    gcc \
    --no-install-recommends

echo "=== Installing Google Chrome ==="
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
apt-get update -qq
apt-get install -y -qq google-chrome-stable

echo "Chrome: $(google-chrome --version)"

echo "=== Installing matching ChromeDriver ==="
CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+\.\d+' | head -1)
CHROME_MAJOR=$(echo $CHROME_VERSION | cut -d. -f1)
echo "Chrome version: $CHROME_VERSION (major: $CHROME_MAJOR)"

# Try exact version first, fallback to latest for that major
DRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip"
wget -q "$DRIVER_URL" -O /tmp/chromedriver.zip 2>/dev/null || {
    echo "Exact version not found, fetching latest for major $CHROME_MAJOR..."
    LATEST=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_MAJOR}")
    echo "Latest: $LATEST"
    wget -q "https://storage.googleapis.com/chrome-for-testing-public/${LATEST}/linux64/chromedriver-linux64.zip" -O /tmp/chromedriver.zip
}

unzip -q /tmp/chromedriver.zip -d /tmp/
mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
chmod +x /usr/local/bin/chromedriver
echo "ChromeDriver: $(chromedriver --version)"

echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Running migrations ==="
python manage.py migrate --no-input

echo "=== Collecting static files ==="
python manage.py collectstatic --no-input

echo "=== Build complete ==="