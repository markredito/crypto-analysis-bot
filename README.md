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

- **OpenAI**: For AI analysis (GPT-4o + o1-mini models)
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

## AI Models & Cost Optimization

This bot uses OpenAI's latest models for optimal performance and cost:

- **Sentiment Analysis**: GPT-4o (2024-08-06) - Optimized for structured JSON output
- **Trading Analysis**: o1-mini (2024-09-12) - Advanced reasoning for complex trading decisions
- **Cost Efficient**: ~90% cheaper than previous GPT-4 implementations
- **Performance**: Faster response times with better analytical accuracy

## Technical Architecture

- **Backend**: Flask (Python 3.9+)
- **Data Sources**: TwelveData API (crypto prices), NewsAPI (sentiment)
- **AI Processing**: OpenAI GPT-4o + o1-mini
- **Email**: SMTP via Gmail
- **Deployment**: Vercel serverless functions
- **Frontend**: Vanilla JavaScript with responsive CSS

## API Rate Limits & Costs

**Free Tier Limits:**
- TwelveData: 800 requests/day
- NewsAPI: 1,000 requests/day  
- OpenAI: Pay-per-use (~$0.01-0.05 per analysis)
- Gmail: No limits for personal use

**Estimated Costs:**
- ~$0.02 per complete analysis (all timeframes)
- ~$0.60 for 30 analyses per month
- Vercel hosting: Free for personal projects

## Disclaimer

This bot provides analysis for educational purposes only. Not financial advice. Always do your own research and never invest more than you can afford to lose.
