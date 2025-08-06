from flask import Flask, request, render_template, jsonify
import requests
import json
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder='../templates')

# For Vercel
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Initialize OpenAI client lazily
def get_openai_client():
    return OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def clean_crypto_data(raw_data, precision=2):
    """Clean and process crypto data - converted from your n8n JavaScript"""
    try:
        # Handle nested data structure
        if isinstance(raw_data, dict) and 'values' in raw_data and 'meta' in raw_data:
            dataset = raw_data
        else:
            return {"error": True, "message": "Invalid data structure"}
        
        if dataset.get('status') != 'ok':
            return {"error": True, "message": f"Dataset status: {dataset.get('status')}"}
        
        meta = dataset['meta']
        raw_values = dataset['values']
        
        # Sort by datetime - handle different datetime formats
        def parse_datetime(dt_str):
            try:
                # Try with Z suffix first
                if dt_str.endswith('Z'):
                    return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                # Try direct parsing
                return datetime.fromisoformat(dt_str)
            except:
                # Fallback to strptime for other formats
                return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        
        sorted_values = sorted(raw_values, key=lambda x: parse_datetime(x['datetime']))
        
        cleaned_data = []
        
        for i, value in enumerate(sorted_values):
            data_point = {
                'ts': parse_datetime(value['datetime']).isoformat(),
                'o': round(float(value['open']), precision),
                'h': round(float(value['high']), precision),
                'l': round(float(value['low']), precision),
                'c': round(float(value['close']), precision)
            }
            
            # Calculate derived metrics
            range_val = data_point['h'] - data_point['l']
            typical_price = (data_point['h'] + data_point['l'] + data_point['c']) / 3
            
            # Add change calculation
            if i > 0:
                prev_close = cleaned_data[i-1]['c']
                data_point['change'] = round(data_point['c'] - prev_close, precision)
                data_point['change_pct'] = round((data_point['c'] - prev_close) / prev_close * 100, precision)
            else:
                data_point['change'] = 0
                data_point['change_pct'] = 0
            
            data_point['range'] = round(range_val, precision)
            data_point['typical_price'] = round(typical_price, precision)
            data_point['body_size'] = round(abs(data_point['c'] - data_point['o']), precision)
            data_point['upper_shadow'] = round(data_point['h'] - max(data_point['o'], data_point['c']), precision)
            data_point['lower_shadow'] = round(min(data_point['o'], data_point['c']) - data_point['l'], precision)
            
            cleaned_data.append(data_point)
        
        # Calculate summary stats
        prices = [d['c'] for d in cleaned_data]
        highs = [d['h'] for d in cleaned_data]
        lows = [d['l'] for d in cleaned_data]
        
        first_price = cleaned_data[0]['c']
        last_price = cleaned_data[-1]['c']
        
        return {
            'instrument': {
                'symbol': meta.get('symbol', 'UNKNOWN'),
                'base': meta.get('currency_base', 'Unknown'),
                'quote': meta.get('currency_quote', 'Unknown'),
                'exchange': meta.get('exchange', 'Unknown'),
                'type': meta.get('type', 'Unknown')
            },
            'timeframe': {
                'interval': meta.get('interval', '15min'),
                'timezone': 'UTC',
                'start': cleaned_data[0]['ts'],
                'end': cleaned_data[-1]['ts'],
                'data_points': len(cleaned_data)
            },
            'summary': {
                'current_price': last_price,
                'period_high': round(max(highs), precision),
                'period_low': round(min(lows), precision),
                'period_open': cleaned_data[0]['o'],
                'total_change': round(last_price - first_price, precision),
                'total_change_pct': round((last_price - first_price) / first_price * 100, precision),
                'volatility': round(max(highs) - min(lows), precision),
                'avg_price': round(sum(prices) / len(prices), precision)
            },
            'ohlc_data': cleaned_data
        }
        
    except Exception as e:
        return {"error": True, "message": str(e)}

def get_timeframe_config(timeframe):
    """Map user timeframe selection to API intervals"""
    configs = {
        '1h': ['1min', '5min'],
        '12h': ['15min', '1h'], 
        '24h': ['1h', '4h'],
        '1m': ['1day', '1week'],
        '3m': ['1week', '1month'],
        '1y': ['1month']
    }
    return configs.get(timeframe, ['1h', '4h'])  # Default to 24h config

def get_outputsize_for_interval(interval):
    """Get appropriate outputsize based on interval to cover reasonable time period"""
    size_map = {
        '1min': 60,    # 1 hour of data
        '5min': 144,   # 12 hours of data  
        '15min': 96,   # 24 hours of data
        '1h': 168,     # 1 week of data
        '4h': 180,     # 1 month of data
        '1day': 90,    # 3 months of data
        '1week': 52,   # 1 year of data
        '1month': 24   # 2 years of data
    }
    return size_map.get(interval, 100)

def get_price_data(ticker, interval):
    """Fetch price data from TwelveData API"""
    url = "https://api.twelvedata.com/time_series"
    params = {
        'symbol': ticker,
        'interval': interval,
        'outputsize': get_outputsize_for_interval(interval),
        'apikey': os.getenv('TWELVEDATA_API_KEY'),
        'type': 'Digital Currency'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching price data: {e}")
        return {"error": True, "message": str(e)}

def get_news_timeframe(timeframe):
    """Map timeframe to appropriate news date range"""
    now = datetime.now()
    
    timeframe_days = {
        '1h': 1,      # Last 1 day for hourly analysis
        '12h': 2,     # Last 2 days for 12h analysis  
        '24h': 3,     # Last 3 days for daily analysis
        '1m': 7,      # Last week for monthly analysis
        '3m': 14,     # Last 2 weeks for quarterly analysis
        '1y': 30      # Last month for yearly analysis (NewsAPI free limit)
    }
    
    days_back = timeframe_days.get(timeframe, 3)
    from_date = (now - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    return from_date

def get_news_data(ticker, timeframe='24h'):
    """Fetch news data from NewsAPI with timeframe-appropriate date range"""
    base_ticker = ticker.split('/')[0]  # Get base currency (e.g., ETH from ETH/USD)
    from_date = get_news_timeframe(timeframe)
    
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': base_ticker,
        'from': from_date,
        'sortBy': 'publishedAt',  # Get most recent first
        'language': 'en',
        'apiKey': os.getenv('NEWSAPI_KEY')
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news data: {e}")
        return {"articles": []}

def analyze_sentiment(articles, timeframe='24h'):
    """Analyze sentiment using OpenAI with comprehensive crypto market analysis"""
    
    # Map timeframe to sentiment analysis context
    timeframe_context = {
        '1h': 'immediate market reactions and breaking news impact',
        '12h': 'short-term sentiment shifts and intraday catalysts',
        '24h': 'daily sentiment trends and recent developments',
        '1m': 'weekly sentiment patterns and medium-term narratives',
        '3m': 'monthly sentiment cycles and longer-term themes',
        '1y': 'quarterly and annual sentiment trends, major market shifts'
    }
    
    context = timeframe_context.get(timeframe, 'recent market sentiment')
    
    system_prompt = f"""You are a highly intelligent and accurate sentiment analyzer specializing in cryptocurrency and financial markets, focusing on {context}.

**CRITICAL: You MUST respond with ONLY valid JSON. No explanatory text, no markdown formatting, no additional commentary.**

**Required JSON Output Format:**
{{
  "overall_sentiment": "Positive/Negative/Neutral",
  "sentiment_score": 0.0,
  "market_impact": "High/Medium/Low", 
  "key_factors": ["factor1", "factor2"],
  "rationale": "Brief explanation",
  "articles_analyzed": 0
}}

**Sentiment Scoring:**
- -1.0 to -0.6 = Strongly negative (major bearish catalyst)
- -0.5 to -0.2 = Moderately negative (minor bearish factor)  
- -0.1 to +0.1 = Neutral (no significant market impact)
- +0.2 to +0.5 = Moderately positive (minor bullish factor)
- +0.6 to +1.0 = Strongly positive (major bullish catalyst)

**Analysis Focus for {timeframe} timeframe:**
- Regulations, adoptions, technical developments, institutional moves
- Source credibility and article recency relative to {timeframe} trading
- Market-moving vs noise for {timeframe} perspective
- Current market context and {context}

**RESPOND WITH VALID JSON ONLY. START YOUR RESPONSE WITH {{ AND END WITH }}**"""
    
    user_prompt = f"News articles to analyze for {timeframe} timeframe:\n{json.dumps(articles)}"
    
    client = get_openai_client()
    response = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)

def generate_trading_analysis(price_data, sentiment_data, timeframe='24h'):
    """Generate trading analysis using OpenAI"""
    
    # Map timeframe to trading style context
    timeframe_context = {
        '1h': 'scalping and ultra-short-term trades',
        '12h': 'intraday trading with quick entries/exits', 
        '24h': 'day trading with swing potential',
        '1m': 'swing trading over days to weeks',
        '3m': 'position trading with medium-term outlook',
        '1y': 'long-term investment and major trend analysis'
    }
    
    trading_style = timeframe_context.get(timeframe, 'day trading')
    
    prompt = f"""You are an expert cryptocurrency trader specializing in {trading_style}. Using the technical data and sentiment analysis below, provide a unified trade recommendation optimized for the {timeframe} timeframe.

DECISION FRAMEWORK:
- BUY: Strong bullish technicals + positive sentiment (>0.2) + volume confirmation
- SELL: Strong bearish technicals + negative sentiment (<-0.2) + volume confirmation  
- HOLD: Mixed signals, low volume, or conflicting timeframes

ANALYSIS METHODOLOGY:
Follow these steps for systematic analysis:

1. **Multi-Timeframe Analysis:** Compare the provided timeframe data
   - Identify trend alignment or divergence between timeframes
   - Note timeframe-specific patterns and signals
   - Focus on the {timeframe} perspective for primary signals

2. **Entry Optimization:** Use shorter timeframe for precise entry timing
   - RSI levels for momentum confirmation
   - MACD signals for trend strength  
   - Key trendlines and breakout/breakdown levels
   - Optimize entry based on selected timeframe context

3. **Trend Confirmation:** Use longer timeframe for broader market context
   - Confirm overall trend direction
   - Identify major support/resistance zones
   - Assess trend strength and sustainability for {timeframe} trades

4. **Sentiment Integration:** Factor sentiment analysis to refine Buy/Sell/Hold decision
   - Strong sentiment + aligned technicals = higher confidence
   - Conflicting sentiment + technicals = reduce position size or wait
   - Major news catalysts may override pure technical signals

TECHNICAL ANALYSIS PRIORITIES:
- Multi-timeframe alignment optimized for {timeframe} trading
- Volume patterns and price-volume relationship
- Key support/resistance from period high/low data  
- Candlestick patterns and price action signals
- Volatility analysis using range and body_size data
- Price momentum using change_pct across timeframes

RISK MANAGEMENT (Adapted for {timeframe}):
- Stop-Loss: Appropriate % based on {timeframe} volatility and typical price swings
- Targets: Risk-reward ratios suitable for {timeframe} holding period
- Position sizing: Adjusted for {timeframe} trade duration and risk profile

REQUIRED OUTPUT FORMAT:

**PRIMARY RECOMMENDATION: [BUY/SELL/HOLD]**
**CONFIDENCE: [High/Medium/Low]**
**TIMEFRAME: [Scalp/Intraday/Swing]**

- **Technical Synopsis:** [3-4 key technical points including volume analysis]
- **Sentiment Impact:** [How news sentiment supports/contradicts technicals]
- **Entry Strategy:** $X.XX [specify if market/limit order]
- **Stop-Loss:** $X.XX (-X.X%) 
- **Primary Target:** $X.XX (+X.X%)
- **Extended Target:** $X.XX (+X.X%) [for aggressive scenarios]
- **Risk-Reward:** X:1

**ALTERNATIVE SCENARIOS:**

**If Bullish Scenario:**
- Entry: $X.XX | Target: $X.XX | Stop: $X.XX

**If Bearish Scenario:**  
- Entry: $X.XX | Target: $X.XX | Stop: $X.XX

**KEY LEVELS TO WATCH:**
- Critical Support: $X.XX
- Critical Resistance: $X.XX
- Volume Threshold: [Normal/High/Low based on recent patterns]

Analyze the provided candlestick data across all timeframes, incorporate volume patterns from the OHLC data, factor in the sentiment analysis, and provide actionable trade recommendations with specific price levels.

Technical Data (candles):
{json.dumps(price_data)}

Sentiment Analysis (timeframe-matched news):
{json.dumps(sentiment_data)}"""
    
    client = get_openai_client()
    response = client.chat.completions.create(
        model="o4-mini-2025-04-16",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content

def markdown_to_html(text):
    """Convert markdown formatting to HTML"""
    import re
    
    # Convert **bold** to <strong>
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    # Convert *italic* to <em>
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    
    # Convert bullet points (- item) to HTML list items
    lines = text.split('\n')
    html_lines = []
    in_list = False
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('- '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            html_lines.append(f'<li>{stripped[2:]}</li>')
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(line)
    
    if in_list:
        html_lines.append('</ul>')
    
    # Join lines and convert line breaks to <br>
    text = '\n'.join(html_lines)
    text = text.replace('\n\n', '<br><br>')
    text = text.replace('\n', '<br>')
    
    return text

def send_email(to_email, ticker, analysis, timeframe='24h'):
    """Send analysis via email"""
    from_email = os.getenv('EMAIL_USER')
    password = os.getenv('EMAIL_PASS')
    
    # Map timeframe to readable format
    timeframe_labels = {
        '1h': 'Hourly',
        '12h': '12-Hour', 
        '24h': 'Daily',
        '1m': 'Monthly',
        '3m': 'Quarterly',
        '1y': 'Yearly'
    }
    
    timeframe_label = timeframe_labels.get(timeframe, 'Daily')
    
    # Convert markdown to HTML
    formatted_analysis = markdown_to_html(analysis)
    
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = f"🚀 {ticker} {timeframe_label} Trading Analysis"
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="background: #1a1a1a; color: white; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px;">
            <h1>🚀 CRYPTO TRADING ALERT</h1>
            <h2>{ticker} Analysis</h2>
        </div>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3>📋 Analysis</h3>
            <div style="background: white; padding: 15px; border-radius: 5px; font-family: 'Courier New', monospace;">{formatted_analysis}</div>
        </div>
        
        <hr>
        <p style="text-align: center; color: #666; font-size: 12px;">
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            <em>Automated Crypto Trading Bot by Mark Redito</em>
        </p>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html_body, 'html'))
    
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(from_email, password)
    server.send_message(msg)
    server.quit()

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"Error loading template: {str(e)}", 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/test')
def test():
    return "Flask app is working! Environment variables loaded."

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        ticker = data.get('ticker')
        timeframe = data.get('timeframe', '24h')
        email = data.get('email')
        
        if not ticker or not email:
            return jsonify({'error': 'Ticker and email are required'}), 400
        
        print(f"Processing analysis for {ticker} with {timeframe} timeframe")
        
        # Get timeframe configuration
        intervals = get_timeframe_config(timeframe)
        price_data = []
        
        for interval in intervals:
            print(f"Fetching {interval} data...")
            raw_data = get_price_data(ticker, interval)
            
            # Check for API errors
            if raw_data.get('error'):
                return jsonify({'error': f'Price data error: {raw_data.get("message")}'}), 500
            
            cleaned = clean_crypto_data(raw_data)
            
            # Check for cleaning errors
            if cleaned.get('error'):
                return jsonify({'error': f'Data processing error: {cleaned.get("message")}'}), 500
                
            price_data.append(cleaned)
        
        print("Fetching news data...")
        # Get news and analyze sentiment
        news_data = get_news_data(ticker, timeframe)
        articles = news_data.get('articles', [])
        
        print(f"Found {len(articles)} articles")
        
        if articles:
            print("Analyzing sentiment...")
            sentiment = analyze_sentiment(articles, timeframe)
        else:
            sentiment = {
                "overall_sentiment": "Neutral",
                "sentiment_score": 0.0,
                "market_impact": "Low",
                "key_factors": ["No recent news"],
                "rationale": "No news articles found",
                "articles_analyzed": 0
            }
        
        print("Generating trading analysis...")
        # Generate trading analysis
        analysis = generate_trading_analysis(price_data, sentiment, timeframe)
        
        print("Sending email...")
        # Send email
        send_email(email, ticker, analysis, timeframe)
        
        return jsonify({'success': True, 'message': 'Analysis sent successfully'})
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to process analysis: {str(e)}'}), 500

# Export the Flask app for Vercel
app = app

if __name__ == '__main__':
    app.run(debug=True)