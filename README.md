# Crypto Analysis Bot (Python/Flask)

A lightweight Flask web app that provides automated crypto trading analysis combining technical indicators with sentiment analysis.

## Features

- **Multi-timeframe Analysis**: 6 timeframe options (1h, 12h, 24h, 1m, 3m, 1y)
- **Technical Analysis**: OHLC data processing, volume analysis, support/resistance
- **News Sentiment**: Real-time sentiment analysis using OpenAI GPT-4
- **AI Trading Recommendations**: Comprehensive buy/sell/hold signals with price targets
- **Email Delivery**: Formatted HTML analysis reports
- **Responsive UI**: Clean, mobile-friendly interface
- **Free Deployment**: Optimized for Vercel's free tier

## Local Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment variables:**
```bash
cp .env.example .env
```
Fill in your API keys in `.env`

3. **Run development server:**
```bash
python app.py
```

## Deploy to Vercel (Free)

1. **Install Vercel CLI:**
```bash
npm install -g vercel
```

2. **Deploy:**
```bash
vercel
```

3. **Add environment variables in Vercel dashboard**

## API Keys Needed

- **OpenAI**: For AI analysis (`gpt-4-turbo-preview`)
- **TwelveData**: For crypto price data (free tier available)
- **NewsAPI**: For sentiment analysis (free tier available)
- **Gmail App Password**: For email sending

## Gmail Setup

1. Enable 2-factor authentication on Gmail
2. Generate an "App Password" for this application
3. Use your Gmail address and the app password in environment variables

## Usage

1. Enter crypto ticker (e.g., "ETH/USD", "BTC/USD")
2. Select analysis timeframe:
   - **Last Hour**: For scalping/ultra-short trades
   - **Last 12 Hours**: For intraday trading
   - **Last 24 Hours**: For day trading (default)
   - **Last Month**: For swing trading
   - **3 Months**: For position trading
   - **Year**: For long-term analysis
3. Enter your email address
4. Click "Get Analysis"
5. Check email for comprehensive trading analysis with entry/exit points

## Family Sharing

Once deployed on Vercel:
- Share the live URL with family
- They only need the website URL and their email
- No technical setup required
- Works on any device