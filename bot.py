import finnhub
import discord
from discord.ext import commands
from datetime import date, timedelta, datetime
from matplotlib.pyplot import hlines, savefig, ylabel
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import os


api_key = None
discord_token = None

with open("api_key.txt") as file:
    api_key = file.read()

with open("discord_token.txt") as file:
    discord_token = file.read()

if api_key is None:
    raise Exception("API key missing")
if discord_token is None:
    raise Exception("Discord bot token missing")

bot = commands.Bot(command_prefix=".")
finnhub_client = finnhub.Client(api_key)

MONTH_TO_QUARTER = {
    '03': "1",
    '06': "2",
    '09': "3",
    '12': "4"
}

MONTHS = {
    "01": 'Jan',
    "02": "Feb",
    "03": "Mar",
    "04": "Apr",
    "05": "May",
    "06": "Jun",
    "07": "Jul",
    "08": "Aug",
    "09": "Sep",
    "10": "Oct",
    "11": "Nov",
    "12": "Dec"
}

CHART_TYPES = set(['1', '5', '15', '30', '60', 'd', 'w', 'm'])


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        # Ignore these errors, this error will trigger when a chat user interacts with another bot with the same prefix
        return
    raise error


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)


@bot.command()
async def price(ctx, symbol=""):
    """Returns the current price, and change for the day for a stock symbol"""
    if len(symbol) == 0:
        await ctx.send("Invalid symbol")
        return

    symbol = symbol.upper()
    data = finnhub_client.quote(symbol)

    if data['c'] == 0:
        await ctx.send("No data found")
        return

    color = 0x000000

    if data['d'] > 0:
        color = discord.Color.green()
    elif data['d'] < 0:
        color = discord.Color.red()

    response = discord.Embed(title=symbol, color=color)

    response.add_field(name="Current price",
                       value=f"{data['c']}", inline=False)
    response.add_field(name="High", value=f"{data['h']}", inline=True)
    response.add_field(name="Low", value=f"{data['l']}", inline=True)

    response.add_field(name=chr(173), value=chr(173))

    trunc_percent = "{:.2f}".format(data['dp'])
    response.add_field(name="Change", value=f"{data['d']}", inline=True)
    response.add_field(name="Percent change",
                       value=f"{trunc_percent}%", inline=True)

    await ctx.send(embed=response)


@bot.command()
async def cprice(ctx, symbol=""):
    """Returns last price for a cryptocurrency"""
    # TODO: finish
    if len(symbol) == 0:
        await ctx.send("Invalid symbol")
        return


@bot.command()
async def earnings(ctx, symbol=""):
    """Returns actual and estimated EPS for past 4 quarters for a stock"""
    if len(symbol) == 0:
        await ctx.send("Invalid symbol")
        return

    earnings_vals = finnhub_client.company_earnings(symbol)
    """
    Example response:
    [{
    "actual": 2.56,
    "estimate": 2.38,
    "period": "2019-03-31",
    "symbol": "AAPL"
    },
    ...
    ]
    """

    if len(earnings_vals) == 0:
        await ctx.send("No data found")
        return

    response = discord.Embed(title=f"Earnings Results for {symbol.upper()}")

    for quarter_results in earnings_vals:
        year, month, day = quarter_results['period'].split("-")
        quarter_num = MONTH_TO_QUARTER[month]  # Q1-Q4
        time_period = f"***Q{quarter_num} {year}***"
        results = f"\n\tEstimated EPS: {quarter_results['estimate']}"
        results += f"\n\tActual EPS: {quarter_results['actual']}"
        trunc_percent = "{:.2f}".format(quarter_results['surprisePercent'])
        results += f"\n\tSurprise: {quarter_results['surprise']}\n\tSurprise Percent: {trunc_percent}%"
        response.add_field(name=time_period, value=results)

    await ctx.send(embed=response)
    return


@bot.command()
async def news(ctx, symbol=""):
    """
    Returns news for a company from 1 year ago to today
    Shows a maximum of 5 events
    """
    if len(symbol) == 0:
        await ctx.send("Invalid symbol")
        return

    from_date = date.today() - timedelta(days=365)
    from_date = from_date.strftime("%Y-%m-%d")
    to_date = date.today().strftime("%Y-%m-%d")

    stock_news = finnhub_client.company_news(symbol, from_date, to_date)[:5]
    if len(stock_news) == 0:
        await ctx.send("No data found")
        return

    today_str = date.today().strftime("%m-%d-%Y")
    yesterday_str = date.today() - timedelta(days=1)
    yesterday_str = yesterday_str.strftime("%m-%d-%Y")

    response = discord.Embed(
        title=f"**News for {symbol.upper()}**", color=discord.Color.blue())

    for event in stock_news:
        date_of_event = datetime.fromtimestamp(
            event["datetime"]).strftime("%m-%d-%Y")

        if date_of_event == today_str:
            date_of_event = "Today"
        elif date_of_event == yesterday_str:
            date_of_event = "Yesterday"

        response.add_field(
            name=event['source'], value=f"\n***{date_of_event}*** - {event['headline']} Link-{event['url']}")

    await ctx.send(embed=response)


@bot.command()
async def trends(ctx, symbol=""):
    """
    Returns analyst recommendations for stock(buy, sell, or hold) on monthly basis
    Will display recommendations for current month, then every previous 6 months for 3 years
    """
    if len(symbol) == 0:
        await ctx.send("Invalid symbol")
        return

    symbol = symbol.upper()

    trends = finnhub_client.recommendation_trends(
        symbol)[:36:6]  # 6 results, going back 6 months for each result

    if len(trends) == 0:
        await ctx.send("No data found")
        return

    response = discord.Embed(
        title=f"Recommendation Trends for {symbol}", color=discord.Color.blue())

    for trend in trends:
        year, month, day = trend['period'].split("-")
        time_period = f"***{MONTHS[month]} {year}***"
        recommendations = f"\n\tStrong buy: {trend['strongBuy']}"
        recommendations += f"\n\tBuy: {trend['buy']}"
        recommendations += f"\n\tHold: {trend['hold']}"
        recommendations += f"\n\tSell: {trend['sell']}"
        recommendations += f"\n\tStrong sell: {trend['strongSell']}"
        response.add_field(name=f"\n{time_period}", value=recommendations)

    await ctx.send(embed=response)


@bot.command()
async def chart(ctx, symbol="", type=""):
    """
    Creates chart for given stock
    Values for chart type are '1', '5', '15', '30', '60', 'd', 'w' or 'm'
    Defaults to 15m candlestick chart if no type given
    """
    if len(symbol) == 0:
        await ctx.send("Invalid symbol")
        return

    if len(type) != 0 and type.lower() not in CHART_TYPES:
        # if no chart type given, default is 15 min candle chart
        await ctx.send("Invalid chart type")
        return

    if type == "":
        type = '15'

    symbol = symbol.upper()
    type = type.upper()

    from_timestamp = datetime.today()

    if type == '1':
        from_timestamp -= timedelta(seconds=60*60*5)
    elif type == '5':
        from_timestamp -= timedelta(seconds=60*60*20)
    elif type == '15':
        from_timestamp -= timedelta(seconds=60*60*60)
    elif type == '30':
        from_timestamp -= timedelta(seconds=60*60*24*10)
    elif type == '60':
        from_timestamp -= timedelta(seconds=60*60*24*20)

    # TODO: seems like d,w,m timeframes aren't available from finnhub for most stocks, use different api
    elif type == 'd':
        from_timestamp -= timedelta(days=150)
    elif type == 'w':
        from_timestamp -= timedelta(days=365)
    elif type == 'm':
        from_timestamp -= timedelta(days=365)

    from_timestamp = int(from_timestamp.timestamp())
    to_timestamp = int(datetime.today().timestamp())

    candles = finnhub_client.stock_candles(
        symbol, type, from_timestamp, to_timestamp)

    if len(candles) == 0 or candles['s'] == "no_data":
        await ctx.send("No data")
        return

    data = pd.DataFrame(candles, index=pd.DatetimeIndex(
        pd.to_datetime(
            candles['t'], unit='s'))).drop(['s', 't'], axis=1)

    data.rename(columns={'o': 'Open', 'c': 'Close',
                'h': 'High', 'l': 'Low', 'v': 'Volume'}, inplace=True)

    filename = str(datetime.now().timestamp()) + symbol + ".png"

    time_period = ""

    if type.isnumeric():
        time_period = type + "m"
    else:
        time_period = type.upper()

    rsi_chart = ta.rsi(data['Close'])
    rsi = mpf.make_addplot(
        rsi_chart, panel=2, ylabel="RSI", secondary_y=False)

    upper_line = pd.DataFrame(rsi_chart)
    lower_line = pd.DataFrame(rsi_chart)
    upper_line["RSI_14"] = [70] * len(upper_line)
    lower_line["RSI_14"] = [30] * len(upper_line)

    rsi_upper_line = mpf.make_addplot(
        upper_line, panel=2, color='r', secondary_y=False)
    rsi_lower_line = mpf.make_addplot(
        lower_line, panel=2, color='g', secondary_y=False)

    mpf.plot(data, type='candle', title=f"{symbol} ({time_period})", style='yahoo', mav=(
        3, 15), volume=True, panel_ratios=(1, 0.2, 0.2), addplot=[rsi, rsi_upper_line, rsi_lower_line],
        savefig=dict(fname=filename, bbox_inches='tight'), scale_padding={'left': 1, 'top': 0.3, 'right': 1, 'bottom': 1})

    await ctx.send(file=discord.File(filename))
    os.remove(filename)
    return


bot.run(discord_token)
