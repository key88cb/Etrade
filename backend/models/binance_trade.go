package models

import "time"

type BinanceTrade struct {
	// 核心字段
	ID        uint64    `gorm:"primaryKey"`          // 使用 uint64 对应 BIGINT
	TradeTime time.Time `gorm:"index;not null"`      // 对应 trade_time (TIMESTAMPTZ)
	Price     float64   `gorm:"not null"`            // 对应 price
	Quantity  float64   `gorm:"column:qty;not null"` // 明确映射到 qty 列

	// 与CSV表结构保持一致
	QuoteQuantity float64 `gorm:"column:quote_qty"` // 对应 quote_qty
	IsBuyerMaker  bool    `gorm:"column:is_buyer_maker"`
	IsBestMatch   bool    `gorm:"column:is_best_match"`
}

/*
这是本地解析导入的校本的内容
           id    price     qty  ...              time  isBuyerMaker  isBestMatch

0  2803461704  4391.83  0.0012  ...  1756684800316508          True         True

1  2803461705  4391.83  0.1529  ...  1756684800316508          True         True

2  2803461706  4391.83  0.0012  ...  1756684800316508          True         True

3  2803461707  4391.82  0.0012  ...  1756684800316508          True         True

4  2803461708  4391.82  0.0012  ...  1756684800316508          True         True



[5 rows x 7 columns]

<class 'pandas.core.frame.DataFrame'>

RangeIndex: 1000000 entries, 0 to 999999

Data columns (total 7 columns):

 #   Column        Non-Null Count    Dtype

---  ------        --------------    -----

 0   id            1000000 non-null  int64

 1   price         1000000 non-null  float64

 2   qty           1000000 non-null  float64

 3   quoteQty      1000000 non-null  float64

 4   time          1000000 non-null  int64

 5   isBuyerMaker  1000000 non-null  bool

 6   isBestMatch   1000000 non-null  bool

dtypes: bool(2), float64(3), int64(2)

memory usage: 40.1 MB

None
*/
