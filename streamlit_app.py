import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
from anthropic import Anthropic
import os
import time

# ============================================
# CALMTRADER - AI INVESTMENT COACH v2.0
# With rate limiting and usage tracking
# ============================================

# Page configuration
st.set_page_config(
    page_title="CalmInvestor - Your AI Investment Coach",
    page_icon="🧘",
    layout="wide"
)

# ============================================
# BETA SETTINGS & RATE LIMITING
# ============================================

# Initialize session state for tracking
if 'question_count' not in st.session_state:
    st.session_state.question_count = 0

if 'last_question_time' not in st.session_state:
    st.session_state.last_question_time = 0

# Free tier limits
FREE_QUESTIONS_PER_SESSION = 3
COOLDOWN_SECONDS = 10

# ============================================
# SYSTEM PROMPT - Your Investment Philosophy
# ============================================

SYSTEM_PROMPT = """You are The Calm Investor, an AI investment coach designed to help long-term investors stay rational during market volatility.

Your core philosophy:
- Short-term price movements are noise, not signal
- Emotional decisions destroy long-term returns
- The best investment strategy is usually to do nothing
- Remind users why they bought in the first place
- Focus on fundamentals, not headlines

Your responses should:
1. Acknowledge their concern without feeding panic
2. Provide context (is this normal volatility?)
3. Reference their original investment thesis
4. Remind them of their time horizon
5. Give them a framework for thinking, not a buy/sell command

Tone: Calm, slightly contrarian to market panic, encouraging long-term thinking.

NEVER say "buy" or "sell". Instead say "consider", "here's the framework", "ask yourself".

Always end with: "What was your original reason for investing? Has that changed?"
"""

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_stock_data(ticker, days=7):
    """Fetch recent stock data"""
    try:
        stock = yf.Ticker(ticker)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days+1)
        hist = stock.history(start=start_date, end=end_date)
        
        if hist.empty:
            return None
            
        info = stock.info
        
        current_price = hist['Close'].iloc[-1]
        week_ago_price = hist['Close'].iloc[0]
        week_change_percent = ((current_price - week_ago_price) / week_ago_price) * 100
        
        return {
            'ticker': ticker.upper(),
            'company_name': info.get('longName', ticker),
            'current_price': current_price,
            'week_change_percent': week_change_percent,
            'week_high': hist['High'].max(),
            'week_low': hist['Low'].min(),
            'sector': info.get('sector', 'Unknown'),
        }
    except:
        return None

def check_rate_limit():
    """Check if user has hit rate limit"""
    current_time = time.time()
    time_since_last = current_time - st.session_state.last_question_time
    
    if time_since_last < COOLDOWN_SECONDS:
        return False, int(COOLDOWN_SECONDS - time_since_last)
    return True, 0

def check_usage_limit():
    """Check if user has exceeded free tier limit"""
    if st.session_state.question_count >= FREE_QUESTIONS_PER_SESSION:
        return False
    return True

def get_ai_advice(portfolio_context, user_question, stock_data=None):
    """Get calm, rational advice from Claude"""
    
    # Check usage limit
    if not check_usage_limit():
        return None
    
    # Check rate limit
    can_proceed, wait_time = check_rate_limit()
    if not can_proceed:
        return f"⏳ Please wait {wait_time} seconds before asking another question."
    
    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "⚠️ API key not configured. Please contact support."
    
    try:
        client = Anthropic(api_key=api_key)
        
        # Build context
        context = f"User's Portfolio Context: {portfolio_context}\n\n"
        context += f"User's Question: {user_question}\n\n"
        
        if stock_data:
            context += f"Current Market Data:\n"
            context += f"- {stock_data['company_name']} ({stock_data['ticker']})\n"
            context += f"- Current Price: ${stock_data['current_price']:.2f}\n"
            context += f"- Week Change: {stock_data['week_change_percent']:+.2f}%\n"
            context += f"- Week Range: ${stock_data['week_low']:.2f} - ${stock_data['week_high']:.2f}\n"
            context += f"- Sector: {stock_data['sector']}\n"
        
        # Call Claude
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": context}
            ]
        )
        
        # Update tracking
        st.session_state.question_count += 1
        st.session_state.last_question_time = time.time()
        
        return message.content[0].text
        
    except Exception as e:
        return f"⚠️ Error getting advice: {str(e)}"

def format_large_number(num):
    """Convert large numbers to readable format"""
    if isinstance(num, str) or num == 'N/A':
        return num
    
    if num >= 1_000_000_000:
        return f"${num / 1_000_000_000:.2f}B"
    elif num >= 1_000_000:
        return f"${num / 1_000_000:.2f}M"
    else:
        return f"${num:,.0f}"

# ============================================
# STREAMLIT UI
# ============================================

# Beta Banner
st.info("🚀 **FREE BETA:** Testing phase. Limited to 3 questions per session. Premium coming soon!")

# Header
st.title("🧘 CalmInvestor")
st.subheader("Your AI Investment Coach")
st.markdown("Stop panic selling. Get calm, rational analysis of your investments.")

# Usage counter
questions_remaining = FREE_QUESTIONS_PER_SESSION - st.session_state.question_count
if questions_remaining > 0:
    st.caption(f"💬 Questions remaining this session: {questions_remaining}")
else:
    st.warning("🚫 You've used all 3 free questions this session. Refresh the page to reset, or upgrade to Premium (coming soon!)")

st.divider()

# Sidebar - Portfolio Context
with st.sidebar:
    st.header("📊 Your Portfolio")
    st.markdown("Tell me about your investments so I can give better advice.")
    
    portfolio_input = st.text_area(
        "What stocks do you own and why?",
        placeholder="Example: I own 10 shares of NVDA for AI growth, 5 shares of AAPL for stability...",
        height=150
    )
    
    time_horizon = st.selectbox(
        "What's your investment timeline?",
        ["Less than 1 year", "1-3 years", "3-5 years", "5+ years", "10+ years"]
    )
    
    st.divider()
    
    st.markdown("### 💡 Pro Tips")
    st.markdown("""
    - Check your portfolio weekly, not daily
    - Focus on why you bought, not today's price
    - Market drops are normal (and opportunities)
    - Time in the market > Timing the market
    """)
    
    st.divider()
    
    # Feedback section
    st.markdown("### 💬 Feedback")
    st.markdown("This is a beta. [Share feedback]https://forms.gle/zhSZMxeF4j8Gx7aE8 or report bugs.")

# Main area - Two tabs
tab1, tab2 = st.tabs(["💬 Ask a Question", "📈 Check a Stock"])

with tab1:
    st.header("Ask Your Investment Coach")
    st.markdown("Feeling anxious about a position? Not sure if you should sell? Ask me.")
    
    user_question = st.text_area(
        "What's on your mind?",
        placeholder="Example: NVDA just dropped 10%. Should I sell? I'm worried about...",
        height=100
    )
    
    if st.button("Get Calm Advice", type="primary", disabled=not check_usage_limit()):
        if not portfolio_input:
            st.warning("⚠️ Please tell me about your portfolio in the sidebar first!")
        elif not user_question:
            st.warning("⚠️ Please ask a question!")
        else:
            with st.spinner("Thinking..."):
                # Build portfolio context
                context = f"Portfolio: {portfolio_input}\nTime Horizon: {time_horizon}"
                
                # Get advice
                advice = get_ai_advice(context, user_question)
                
                # Display
                if advice and not advice.startswith("⏳") and not advice.startswith("⚠️"):
                    st.success("Here's my take:")
                    st.markdown(advice)
                    
                    # Show upgrade prompt if this was the last free question
                    if st.session_state.question_count >= FREE_QUESTIONS_PER_SESSION:
                        st.info("🎉 Want unlimited questions? Premium tier coming soon. [Join waitlist](#)")
                else:
                    st.warning(advice)

with tab2:
    st.header("Quick Stock Check")
    st.markdown("Get a calm analysis of any stock in your portfolio.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        ticker = st.text_input("Enter Stock Ticker", placeholder="AAPL").upper()
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        check_button = st.button("Check Stock", type="primary", disabled=not check_usage_limit())
    
    if check_button and ticker:
        with st.spinner(f"Analyzing {ticker}..."):
            # Get stock data
            stock_data = get_stock_data(ticker)
            
            if not stock_data:
                st.error(f"❌ Couldn't find data for {ticker}. Check the ticker symbol.")
            else:
                # Display stock info
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Current Price",
                        f"${stock_data['current_price']:.2f}"
                    )
                
                with col2:
                    st.metric(
                        "Week Change",
                        f"{stock_data['week_change_percent']:+.2f}%"
                    )
                
                with col3:
                    st.metric(
                        "Week Range",
                        f"${stock_data['week_low']:.2f} - ${stock_data['week_high']:.2f}"
                    )
                
                st.divider()
                
                # Get AI analysis
                if portfolio_input:
                    context = f"Portfolio: {portfolio_input}\nTime Horizon: {time_horizon}"
                    question = f"What should I know about {ticker}'s recent performance? Should I be concerned?"
                    
                    with st.spinner("Getting AI analysis..."):
                        advice = get_ai_advice(context, question, stock_data)
                        
                        if advice and not advice.startswith("⏳") and not advice.startswith("⚠️"):
                            st.markdown("### 🤖 AI Analysis")
                            st.info(advice)
                        else:
                            st.warning(advice)
                else:
                    st.warning("⚠️ Add your portfolio info in the sidebar to get personalized analysis!")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>Built by a 15-year-old investor who learned that staying calm beats reacting to headlines.</p>
    <p><small>Not financial advice. Always do your own research.</small></p>
    <p><small>Questions? Feedback? Contact: thecalminvestor34@gmail.com</small></p>
</div>
""", unsafe_allow_html=True)
