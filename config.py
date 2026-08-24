BIST_STOCKS = [
    "THYAO.IS",  
    "AKBNK.IS",  
    "GARAN.IS",  
    "ASELS.IS",  
    "EREGL.IS",  
    "KCHOL.IS",  
    "SISE.IS",   
    "BIMAS.IS",  
]

BACKTEST_YEARS = 2

PIVOT_METHODS = ["classic", "fibonacci", "camarilla", "demark", "woodie"]

# "Touch": fiyatın pivot seviyesine ne kadar yaklaştığıdır.
TOUCH_THRESHOLD_PCT = 0.001

# "Break": fiyatın pivot seviyesini ne kadar geçtiğidir.
BREAK_THRESHOLD_PCT = 0.002

# Confluence zone: farklı yöntemlerden gelen pivot seviyelerinin, birbirine bu yüzde kadar yakın olması durumunda "confluence" sayılmasıdır.
CONFLUENCE_TOLERANCE_PCT = 0.003

DATABASE_PATH = "data/bist_pivot.db"