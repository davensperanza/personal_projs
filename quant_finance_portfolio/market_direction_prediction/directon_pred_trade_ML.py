# %%
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
import tqdm
import datetime

tickers = ['NVDA', 'GOOGL', 'AAPL', 'GOOG', 'MSFT', 'AMZN', 'TSM', 'AVGO', 'META', 'TSLA', 'SMCI']
tickers = ['ACN']

forex_tickers = [
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "USDCHF=X",
    "AUDUSD=X",
    "USDCAD=X",
    "NZDUSD=X",
    "EURGBP=X",
    "EURJPY=X",
    "GBPJPY=X",
    "EURCHF=X"
]

# for log and output save
now = datetime.datetime.now()
date = now.strftime("%Y-%m-%d %H:%M:%S")

# %%
def load_stock(start_date, stock='NVDA'):
    df = yf.download(stock, start=start_date, end='2026-01-01', interval='1d')

    if isinstance(df.columns, pd.MultiIndex):
        lvl0 = df.columns.get_level_values(0)
        lvl1 = df.columns.get_level_values(1)

        if 'Close' in lvl0:
            df.columns = lvl0
        elif 'Close' in lvl1:
            df.columns = lvl1

    df = df.loc[:, ~df.columns.duplicated()].copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.dropna(subset=['Close']).copy()
    return df

# %%
# here i will import the data for creating the time series

def return_calculator(stock):
    data = load_stock(start_date='2020-01-01', stock=stock)

    plt.plot(data['Close'])
    plt.title(f'Price series of {stock}')
    # plt.show()

    data.head()

    # %%
    # new feature selected by correlation

    nxxs, nxs, ns, nm, nb = 3,5,10,20,50

    data['ret_1'] = data['Close'].pct_change() # (data['Close]-data['Close].shift(1))/data['Close].shift(1) -1
    data['ret_5'] = data['Close'].pct_change(5)
    data['ret_10'] = data['Close'].pct_change(10)
    
    data[f'MA{ns}'] = data['Close'].rolling(ns).mean()
    data[f'MA{nm}'] = data['Close'].rolling(nm).mean()
    data[f'MA{nb}'] = data['Close'].rolling(nb).mean()

    # better to calculate the distance (NORMALIZED) from the MA
    data[f'MA{ns}dis'] = (data['Close']/data[f'MA{ns}'])-1
    data[f'MA{nm}dis'] = (data['Close']/data[f'MA{nm}'])-1
    data[f'MA{nb}dis'] = (data['Close']/data[f'MA{nb}'])-1

    # exponential moving avg
    def multiplier(n):
        return 2 / (n + 1)

    def ema(n):
        col = f'EMA{n}'
        alpha = multiplier(n)

        data[col] = np.nan
        data.loc[data.index[0], col] = data['Close'].iloc[0]

        for i in range(1, len(data)):
            data.loc[data.index[i], col] = (
                alpha * data['Close'].iloc[i]
                + (1 - alpha) * data.loc[data.index[i - 1], col]
            )

    ema(ns)
    ema(nm)
    ema(nb)

    # ema distances
    data[f'EMA{ns}dis'] = data['Close']/data[f'EMA{ns}'] - 1
    data[f'EMA{nm}dis'] = data['Close']/data[f'EMA{nm}'] - 1
    data[f'EMA{nb}dis'] = data['Close']/data[f'EMA{nb}'] - 1

    # z-score
    data[f'z{nxxs}'] = (data['Close']-data['Close'].rolling(nxxs).mean())/data['Close'].rolling(nxxs).std()
    data[f'z{nxs}'] = (data['Close']-data['Close'].rolling(nxs).mean())/data['Close'].rolling(nxs).std()
    data[f'z{ns}'] = (data['Close']-data['Close'].rolling(ns).mean())/data['Close'].rolling(ns).std()

    # volatility
    data[f'vol{nxs}'] = data['Close'].rolling(nxs).std()
    data[f'vol{ns}'] = data['Close'].rolling(ns).std()
    data[f'vol{nm}'] = data['Close'].rolling(nm).std()

    # bollinger bands
    # 2std aroud the moving avg, better to calculate the distance from the boundaries
    data[f'bb_upper_{nm}_dis'] = data['Close']/(data[f'MA{nm}'] + 2*data[f'vol{nm}']) - 1
    data[f'bb_lower_{nm}_dis'] = data['Close']/(data[f'MA{nm}'] - 2*data[f'vol{nm}']) - 1

    # momentum (no leakage)
    data[f'momentum{ns}'] = data['Close'] - data['Close'].shift(ns)
    data[f'momentum{nm}'] = data['Close'] - data['Close'].shift(nm)

    data['target'] = (data['ret_1'].shift(-1) > 0).astype(int)

    features = ['bb_lower_20_dis','MA20dis','MA50dis', 'z5' , 'EMA20dis','EMA50dis','MA10dis','EMA10dis','z3','ret_1']


    # %%
    # define train and test split

    # train_size = round(len(data) * 0.7)

    split_date = '2024-06-30'

    train = data.loc[data.index < split_date]
    test = data.loc[data.index > split_date]

    train = train.copy()
    test = test.copy()

    # %%
    # creation of prediction column

    # model selected: 
    n_estimators= 100
    max_depth= 5
    learning_rate= 0.15
    subsample= 0.7
    colsample_bytree= 0.7

    threshold = 0.6

    model = XGBClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        random_state=42
    )

    model.fit(train[features],train['target'])

    test['prediction'] = model.predict(test[features])
    test['prediction_prob'] = model.predict_proba(test[features])[:,1]

    # evaluate model

    test['signal'] = 0 # inside the threshold i dont want to trade

    test.loc[test['prediction_prob'] > threshold, 'signal'] = 1
    test.loc[test['prediction_prob'] < (1-threshold), 'signal'] = -1


    # %%
    # trade strategy --> ALL EQUAL ENTRY

    # position need to be shifted
    test['position'] = test['signal'].shift(1)

    # same as above
    # test['future_ret'] = test['ret_1'].shift(-1)
    # test['strategy_ret'] = test['prediction'] * test['future_ret']

    # when the position is 1 I'm following the prediction and so I'm LONG in, viceversa if position is -1 (the next day prediction is 0 so red candle)
    test['strategy_return'] = test['position'] * test['ret_1']
    test['strategy_return'] = test['strategy_return'].fillna(0) # first rows will be NaN because of the shifts

    # EQUITY
    test['equity'] = (1 + test['strategy_return']).cumprod()
    test['buy_and_hold'] = (1 + test['ret_1']).cumprod()

    # adding costs
    cost = 0.001 # per transaction

    test['trade'] = test['position'].diff().abs()
    test['trade'] = test['trade'].fillna(0)

    test['strategy_ret_net'] = test['strategy_return'] - cost * test['trade'] * test['equity']
    test['equity_net'] = (1 + test['strategy_ret_net'].fillna(0)).cumprod()

    # plot results
    plt.plot(test['buy_and_hold'],label='buy and hold')
    plt.plot(test['equity'],label='strategy')
    plt.plot(test['equity_net'],label='strategy_net')
    plt.title(stock)
    plt.legend()
    # plt.show()

    # %%
    return {
        'ticker':stock,
        'buy_and_hold':test['buy_and_hold'].iloc[-1],
        'equity':test['equity'].iloc[-1],
        'equity_net':test['equity_net'].iloc[-1]
        }

def main():
    results = []
    for stock in tqdm.tqdm(forex_tickers):
        res = return_calculator(stock)
        results.append(res)

    df = pd.DataFrame(results)
    return df

if __name__ == '__main__':
    df = main()
    print(df)

    df.to_excel(f"from_work/PYTHON/mytry/algo/output/result_trading_{date}.xlsx", index = False)