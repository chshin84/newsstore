# FMP (Financial Modeling Prep) API Documentation

Comprehensive financial data API. Base URL: `https://financialmodelingprep.com/stable/`

Legacy endpoints (https://financialmodelingprep.com/v3/ or https://financialmodelingprep.com/v4/) have been discontinued and are no longer supported. You must use https://financialmodelingprep.com/stable/

Include your API key in the request header as: apikey: YOUR_API_KEY or append ?apikey=YOUR_API_KEY at the end of every request.When adding the API key to your requests, ensure to use &apikey= if other query parameters already exist in the endpoint.

Do not assume endpoints have parameters other than the ones explicitly specified for each endpoint.

---

# Search

## Search

### Stock Symbol Search

Easily find the ticker symbol of any stock with the FMP Stock Symbol Search API. Search by symbol across multiple global markets.

The FMP Stock Symbol Search API allows users to quickly and efficiently locate stock ticker symbols. Whether you're searching for U.S. stocks, international equities, or ETFs, this API provides fast, reliable results. Key features include: Simple Search: Enter a company name or ticker symbol to retrieve essential details like the symbol, company name, exchange, and currency. Global Market Access: Search across major stock exchanges, including NASDAQ, NYSE, and more. Accurate and Up-to-Date: The API delivers real-time results, ensuring you're always working with the latest ticker information. The Stock Symbol Search API is perfect for traders, investors, or anyone needing quick access to stock symbols across different markets.

**Endpoint:** `https://financialmodelingprep.com/stable/search-symbol?query=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| query* | string | AAPL |
| limit | number | 50 |
| exchange | string | NASDAQ |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "currency": "USD",
    "exchangeFullName": "NASDAQ Global Select",
    "exchange": "NASDAQ"
  }
]
```

---

### Company Name Search

Search for ticker symbols, company names, and exchange details for equity securities and ETFs listed on various exchanges with the FMP Name Search API. This endpoint is useful for retrieving ticker symbols when you know the full or partial company or asset name but not the symbol identifier.

The FMP Name Search API provides an easy way to find the ticker symbols and exchange information for companies and ETFs. This endpoint is useful for retrieving ticker symbols when you know the company or asset name but not the symbol identifier. Key Features of the Name Search API Simple Company Name Lookup: Enter a company or asset name, and retrieve the corresponding ticker symbol, company name, and exchange details. Equity Securities and ETFs: Supports searches for a variety of listed equity securities and exchange-traded funds (ETFs) across major exchanges. Accurate and Up-to-Date Data: Receive real-time, accurate search results, ensuring you're always working with the latest available information. How Investors and Analysts Can Benefit Quick Symbol Lookup: Easily locate ticker symbols when you know the company name but not the corresponding symbol. Broad Market Coverage: Search across multiple exchanges for both domestic and international companies, helping you stay informed about different markets. Streamlined Workflow: Enhance your research and investment decisions by quickly identifying the correct symbols for analysis or trade execution.

**Endpoint:** `https://financialmodelingprep.com/stable/search-name?query=AA`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| query* | string | AA |
| limit | number | 50 |
| exchange | string | NASDAQ |

**Example Response**

```json
[
  {
    "symbol": "AAGUSD",
    "name": "AAG USD",
    "currency": "USD",
    "exchangeFullName": "CCC",
    "exchange": "CRYPTO"
  }
]
```

---

### Search Cik

Easily retrieve the Central Index Key (CIK) for publicly traded companies with the FMP CIK API. Access unique identifiers needed for SEC filings and regulatory documents for a streamlined compliance and financial analysis process.

The FMP CIK API is an essential tool for financial professionals, compliance officers, and analysts who need to quickly and accurately retrieve the Central Index Key (CIK) for a specific company. The CIK is a unique identifier used by the U.S. Securities and Exchange Commission (SEC) to track company filings, making it crucial for accessing corporate disclosures and financial data. Key Features of the CIK API Quick CIK Lookup: Retrieve a company&rsquo;s CIK by entering its symbol or name, allowing for efficient access to SEC filings and other regulatory information. Essential for Compliance: Ensure accurate and timely access to SEC filings for regulatory compliance and corporate governance purposes. Comprehensive Market Coverage: Search for CIKs across companies listed on major U.S. stock exchanges like NASDAQ and the NYSE. The CIK API is invaluable for anyone dealing with corporate filings and compliance, providing seamless access to essential company identifiers. Example: Streamlined SEC Filings: A compliance officer can use the CIK API to quickly find a company&rsquo;s CIK number and use it to retrieve all relevant SEC filings. This enables efficient monitoring of regulatory disclosures and financial statements.

**Endpoint:** `https://financialmodelingprep.com/stable/search-cik?cik=320193`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| cik* | string | 320193 |
| limit | number | 50 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "companyName": "Apple Inc.",
    "cik": "0000320193",
    "exchangeFullName": "NASDAQ Global Select",
    "exchange": "NASDAQ",
    "currency": "USD"
  }
]
```

---

### CUSIP

Easily search and retrieve financial securities information by CUSIP number using the FMP CUSIP API. Find key details such as company name, stock symbol, and market capitalization associated with the CUSIP.

The FMP CUSIP API allows users to quickly retrieve comprehensive financial information linked to a specific CUSIP number (Committee on Uniform Securities Identification Procedures). This nine-character alphanumeric code uniquely identifies financial securities, making it an essential tool for investors, traders, and analysts. Key features of the CUSIP API include: Accurate Identification: Find stock symbols and company names associated with specific CUSIP numbers, ensuring precise identification of securities. Comprehensive Data: Retrieve relevant financial details, including market capitalization, alongside CUSIP and stock symbol information. Versatility: The API supports various types of securities, including stocks, bonds, and mutual funds, offering a broad range of search capabilities across multiple financial markets. This API is a valuable resource for financial professionals who need to identify and analyze securities efficiently by their CUSIP. Example: A trader can use the CUSIP API to instantly locate the CUSIP number and market capitalization for Apple Inc. by simply searching for the stock symbol &ldquo;AAPL,&rdquo; streamlining the research process before executing a trade.

**Endpoint:** `https://financialmodelingprep.com/stable/search-cusip?cusip=037833100`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| cusip* | string | 037833100 |

**Example Response**

```json
[
  {
    "symbol": "AAPL.MX",
    "companyName": "Apple Inc.",
    "cusip": "037833100",
    "marketCap": 79126074220160
  }
]
```

---

### Search Isin

Easily search and retrieve the International Securities Identification Number (ISIN) for financial securities using the FMP ISIN API. Find key details such as company name, stock symbol, and market capitalization associated with the ISIN.

The FMP ISIN API allows users to quickly retrieve comprehensive financial information linked to a specific ISIN (International Securities Identification Number). This twelve-character alphanumeric code uniquely identifies financial securities globally, making it an essential tool for investors, traders, and financial analysts. Key features of the ISIN API include: Accurate Identification: Quickly find stock symbols and company names associated with a specific ISIN, ensuring precise identification of global securities. Comprehensive Data: Retrieve relevant financial details such as the company name, stock symbol, ISIN, and market capitalization. Global Coverage: The ISIN API supports a wide range of international securities, including stocks, bonds, and mutual funds, offering a broad range of search capabilities across global markets. This API is a valuable resource for financial professionals needing to identify and analyze securities efficiently by their ISIN for global investments or research. Example: An investor can use the ISIN API to locate the ISIN and market capitalization for Apple Inc. by searching for the stock symbol &ldquo;AAPL,&rdquo; streamlining global investment research.

**Endpoint:** `https://financialmodelingprep.com/stable/search-isin?isin=US0378331005`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| isin* | string | US0378331005 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "isin": "US0378331005",
    "marketCap": 3900351299800
  }
]
```

---

### Stock Screener

Discover stocks that align with your investment strategy using the FMP Stock Screener API. Filter stocks based on market cap, price, volume, beta, sector, country, and more to identify the best opportunities.

The FMP Company Stock Screener API is a versatile tool designed to help investors find stocks that meet their specific investment criteria. This API is essential for: Customizable Stock Searches: Screen stocks based on a wide range of criteria, including market cap, price, trading volume, beta, sector, and country. Tailor your searches to match your investment goals. Financial Criteria Filters: Go beyond basic metrics by screening stocks based on financial performance indicators such as profitability, growth, and valuation metrics, ensuring you find stocks that fit your financial strategy. Investment Opportunities: Use the Stock Screener API to build watchlists, identify new investment opportunities, and perform in-depth portfolio analysis. Whether you&rsquo;re a beginner or an experienced investor, this API is a valuable resource for discovering stocks that align with your investment approach. Example Building a Watchlist: An investor interested in technology stocks with a market cap of over $10 billion can use the Stock Screener API to filter and create a watchlist of potential investment opportunities. The investor can further refine the list based on other criteria such as beta and trading volume.

**Endpoint:** `https://financialmodelingprep.com/stable/company-screener`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| marketCapMoreThan | number | 1000000 |
| marketCapLowerThan | number | 10000000000000 |
| sector | string | Technology |
| industry | string | Consumer Electronics |
| betaMoreThan | number | 0.5 |
| betaLowerThan | number | 1.5 |
| priceMoreThan | number | 10 |
| priceLowerThan | number | 500 |
| dividendMoreThan | number | 0.5 |
| dividendLowerThan | number | 2 |
| volumeMoreThan | number | 1000 |
| volumeLowerThan | number | 100000000 |
| exchange | string | NASDAQ |
| country | string | US |
| isEtf | boolean | false |
| isFund | boolean | false |
| isActivelyTrading | boolean | true |
| page | number | 0 |
| limit | number | 1000 |
| includeAllShareClasses | boolean | false |

**Example Response**

```json
[
  {
    "symbol": "WIMA",
    "companyName": "WisdomTree International Adaptive Moving Average Fund",
    "marketCap": null,
    "sector": "Financial Services",
    "industry": "Asset Management",
    "beta": null,
    "price": 41.3753,
    "lastAnnualDividend": null,
    "volume": 9247,
    "exchange": "NASDAQ Global Market",
    "exchangeShortName": "NASDAQ",
    "country": "US",
    "isEtf": false,
    "isFund": true,
    "isActivelyTrading": true
  }
]
```

---

### Exchange Variants

Search across multiple public exchanges to find where a given stock symbol is listed using the FMP Exchange Variants API. This allows users to quickly identify all the exchanges where a security is actively traded.

The FMP Exchange Variants API is a powerful tool that provides essential data on where a particular stock is listed across different global exchanges. This API is critical for: Multi-Exchange Search: Easily find all public exchanges where a specific stock is listed, ensuring you have a complete understanding of a company's trading activity worldwide. Detailed Stock Information: The API returns not only the exchanges where a stock is listed but also includes key financial data such as price, market cap, volume, and beta, allowing for a thorough analysis of the stock. Broad Market Coverage: With support for major international exchanges, users can access data from global markets, making it easier to track securities listed in different regions. This API is a valuable resource for investors, traders, and analysts who need a global view of where securities are traded. Example: A trader looking for Apple Inc. (AAPL) can use the Exchange Variants API to retrieve a list of exchanges where Apple&rsquo;s stock is traded, along with crucial financial data like market cap, price range, and average trading volume.

**Endpoint:** `https://financialmodelingprep.com/stable/search-exchange-variants?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "price": 262.82,
    "beta": 1.086,
    "volAvg": 44645993,
    "mktCap": 3900351299800,
    "lastDiv": 1.05,
    "range": "195.07-316.94",
    "changes": 3.24,
    "companyName": "Apple Inc.",
    "currency": "USD",
    "cik": "0000320193",
    "isin": "US0378331005",
    "cusip": "037833100",
    "exchange": "NASDAQ Global Select",
    "exchangeShortName": "NASDAQ",
    "industry": "Consumer Electronics",
    "website": "https://www.apple.com",
    "description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide. The company offers iPhone, a line of smartphones; Mac, a line of personal computers; iPad, a line of multi-purpose tablets; and wearables, home, and accessories comprising AirPods, Apple TV, Apple Watch, Beats products, and HomePod. It also provides AppleCare support and cloud services; and operates various platforms, including the App Store that allow customers to discov...",
    "ceo": "Timothy D. Cook",
    "sector": "Technology",
    "country": "US",
    "fullTimeEmployees": "164000",
    "phone": "(408) 996-1010",
    "address": "One Apple Park Way",
    "city": "Cupertino",
    "state": "CA",
    "zip": "95014",
    "dcfDiff": 162.74174,
    "dcf": 144.59825927349374,
    "image": "https://images.financialmodelingprep.com/symbol/AAPL.png",
    "ipoDate": "1980-12-12",
    "defaultImage": false,
    "isEtf": false,
    "isActivelyTrading": true,
    "isAdr": false,
    "isFund": false
  }
]
```

---

# Directory

## Directory

### Company Symbols List

Easily retrieve a comprehensive list of financial symbols with the FMP Company Symbols List API. Access a broad range of stock symbols and other tradable financial instruments from various global exchanges, helping you explore the full range of available securities.

The FMP Company Symbols List API is a valuable resource for investors, traders, and financial analysts who need to quickly obtain a complete list of symbols for publicly traded companies and financial instruments. This API is essential for: Comprehensive Symbol Retrieval: Gain access to a vast database of stock symbols, including equities, ETFs, and other financial instruments across global exchanges. Multi-Market Coverage: Explore a wide variety of symbols from major stock exchanges around the world, ensuring that you have the necessary data to make informed trading decisions. Accurate Company Information: Each symbol comes with relevant details such as the company name, providing context for each financial instrument in the list. This API is ideal for those who need a quick and easy way to retrieve a complete list of stock symbols or financial instruments across multiple markets.

**Endpoint:** `https://financialmodelingprep.com/stable/stock-list`

**Example Response**

```json
[
  {
    "symbol": "6898.HK",
    "companyName": "China Aluminum Cans Holdings Limited"
  }
]
```

---

### Financial Statement Symbols List

Access a comprehensive list of companies with available financial statements through the FMP Financial Statement Symbols List API. Find companies listed on major global exchanges and obtain up-to-date financial data including income statements, balance sheets, and cash flow statements, are provided.

The FMP Financial Statement Symbols List API provides a complete list of companies for which financial statements are available through our API. This endpoint is essential for: Comprehensive Company Coverage: Discover all companies with available financial statements, including those listed on major exchanges like the NYSE and NASDAQ, as well as international exchanges. Access to Global Financial Data: Gain insights into companies from around the world by accessing their financial statements through this extensive symbol list. Up-to-Date Information: Stay informed with regularly updated lists, ensuring you have access to the latest financial statements for public companies. Example: An investor can use the Financial Statement Symbols List API to find the ticker symbol for a company they are interested in, access its financial statements, and make informed investment decisions based on the latest available data.

**Endpoint:** `https://financialmodelingprep.com/stable/financial-statement-symbol-list`

**Example Response**

```json
[
  {
    "symbol": "6898.HK",
    "companyName": "China Aluminum Cans Holdings Limited",
    "tradingCurrency": "HKD",
    "reportingCurrency": "HKD"
  }
]
```

---

### CIK List

Access a comprehensive database of CIK (Central Index Key) numbers for SEC-registered entities with the FMP CIK List API. This endpoint is essential for businesses, financial professionals, and individuals who need quick access to CIK numbers for regulatory compliance, financial transactions, and investment research.

The FMP CIK List API provides an extensive and searchable database of CIK numbers assigned to SEC-registered entities. A CIK number serves as a unique identifier required for many regulatory filings and financial transactions, making it a crucial tool for: &nbsp; Investment Research: Gain insights into institutional investment patterns through CIK-linked 13F filings, helping you understand equity holdings and market sentiment. Regulatory Compliance: Easily retrieve CIK numbers to ensure compliance with SEC regulations and reporting requirements. Portfolio Management: Track the CIK numbers of key institutional investors, allowing for enhanced portfolio management and market analysis. This API is an invaluable resource for anyone involved in the financial industry, including investment analysts, portfolio managers, and compliance officers, providing access to the CIK numbers that underpin many SEC filings. Example: A portfolio manager can use the CIK List API to retrieve the CIK number of an institutional investor from recent 13F filings, allowing them to analyze the investor&rsquo;s equity holdings and make informed portfolio decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/cik-list?page=0&limit=1000`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| page | number | 0 |
| limit | number | 1000 |

**Example Response**

```json
[
  {
    "cik": "0002036063",
    "companyName": "LUZ Capital Partners, LLC"
  }
]
```

---

### Symbol Changes List

Stay informed about the latest stock symbol changes with the FMP Stock Symbol Changes API. Track changes due to mergers, acquisitions, stock splits, and name changes to ensure accurate trading and analysis.

The FMP Stock Symbol Changes API provides comprehensive data on recent stock symbol changes. This API is essential for: Accurate Trading: Symbol changes can occur for various reasons, including mergers, acquisitions, stock splits, and company name changes. Staying up-to-date with these changes ensures that your trading activities are accurate and error-free. Portfolio Management: By tracking symbol changes, you can ensure that your investment portfolio reflects the correct and current stock symbols, helping you avoid any discrepancies in your holdings. Efficient Stock Tracking: The API makes it easy to find the latest stock symbols, allowing you to quickly locate the stocks you need for trading, research, or analysis. This API is a valuable tool for traders, investors, and analysts who need to keep track of symbol changes to maintain the accuracy of their financial activities. Example: Trading Accuracy: A trader might use the Stock Symbol Changes API to update their trading platform with the latest stock symbols after a company undergoes a merger and changes its symbol. This ensures that their trades are executed correctly without any errors due to outdated information

**Endpoint:** `https://financialmodelingprep.com/stable/symbol-change`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| invalid | string | false |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "date": "2025-02-03",
    "companyName": "XPLR Infrastructure, LP Common Units representing limited partner interests",
    "oldSymbol": "NEP",
    "newSymbol": "XIFR"
  }
]
```

---

### ETF Symbol Search

Quickly find ticker symbols and company names for Exchange Traded Funds (ETFs) using the FMP ETF Symbol Search API. This tool simplifies identifying specific ETFs by their name or ticker.

The FMP ETF Symbol Search API allows users to efficiently locate the ticker symbols and names of various Exchange Traded Funds (ETFs). This API is essential for: Simple ETF Lookup: Access a database of ETF symbols and company names with minimal effort. By searching with a company name or part of it, users can quickly find relevant ETF symbols. Fast, Accurate Data: The API delivers up-to-date information, ensuring users are provided with the latest ETF symbols and names across multiple exchanges. Focus on ETFs: The API is designed specifically for ETF-related searches, making it an invaluable resource for investors, traders, and analysts focusing on this market segment.

**Endpoint:** `https://financialmodelingprep.com/stable/etf-list`

**Example Response**

```json
[
  {
    "symbol": "GULF",
    "name": "WisdomTree Middle East Dividend Fund"
  }
]
```

---

### Actively Trading List

List all actively trading companies and financial instruments with the FMP Actively Trading List API. This endpoint allows users to filter and display securities that are currently being traded on public exchanges, ensuring you access real-time market activity.

The FMP Actively Trading List API provides a comprehensive view of all companies and financial instruments actively traded across public exchanges. This API is essential for: Real-Time Market Monitoring: Stay updated with a list of companies and financial instruments that are currently being traded on global exchanges. Investment Opportunities: Quickly identify active securities to capitalize on current market movements, helping traders and investors make informed decisions. Customizable Filtering: Filter securities based on exchange, industry, or region, ensuring that you find the exact instruments relevant to your trading or investment strategy. This API is an invaluable tool for investors, traders, and analysts who need real-time data on actively traded securities to guide their decisions in the fast-moving financial markets. Example: A day trader can use the Actively Trading List API to retrieve a list of stocks that are currently being traded on the NASDAQ exchange, allowing them to focus on high-liquidity securities for potential trades throughout the day.

**Endpoint:** `https://financialmodelingprep.com/stable/actively-trading-list`

**Example Response**

```json
[
  {
    "symbol": "6898.HK",
    "name": "China Aluminum Cans Holdings Limited"
  }
]
```

---

### Earnings Transcript List

Access available earnings transcripts for companies with the FMP Earnings Transcript List API. Retrieve a list of companies with earnings transcripts, along with the total number of transcripts available for each company.

The FMP Earnings Transcript List API provides users with essential data on the availability of earnings transcripts for various companies. This API is ideal for financial analysts, investors, and researchers looking to track earnings performance over time. Identify Available Transcripts: Quickly access a list of companies with earnings transcripts, complete with the number of available transcripts for each. Support Earnings Analysis: Use the transcript count to further analyze earnings call data and gain insights into company performance. Track Historical Data: Discover companies with multiple transcripts to track earnings calls over different quarters or years. Example Use Case An investor looking to analyze a company&rsquo;s earnings performance over several quarters can use the Earnings Transcript List API to identify companies with multiple earnings call transcripts and retrieve the necessary documents for deeper financial analysis.

**Endpoint:** `https://financialmodelingprep.com/stable/earnings-transcript-list`

**Example Response**

```json
[
  {
    "symbol": "MCUJF",
    "companyName": "Medicure Inc.",
    "noOfTranscripts": "16"
  }
]
```

---

### Available Exchanges

Access a complete list of supported stock exchanges using the FMP Available Exchanges API. This API provides a comprehensive overview of global stock exchanges, allowing users to identify where securities are traded and filter data by specific exchanges for further analysis.

The FMP Available Exchanges API offers users a detailed listing of all supported stock exchanges, providing valuable information for investors, traders, and researchers who want to understand where securities are traded. Key features include: Global Exchange List: Retrieve a complete list of supported exchanges from around the world, including major stock exchanges such as NYSE, NASDAQ, and more. Exchange Name and Short Name: Get both the full exchange name and the short code for easy identification and filtering. Data Filtering by Exchange: Use this list to filter further queries based on specific exchanges, ensuring focused and accurate data retrieval for your needs. This API is essential for those looking to organize or filter financial data based on stock exchange information. Example Use Case A financial analyst can use the Available Exchanges API to create a customized dashboard that filters stock price data by different exchanges, ensuring they track securities relevant to specific markets.

**Endpoint:** `https://financialmodelingprep.com/stable/available-exchanges`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| extended | boolean | false |

**Example Response**

```json
[
  {
    "exchange": "AMEX",
    "name": "New York Stock Exchange Arca",
    "countryName": "United States of America",
    "countryCode": "US",
    "symbolSuffix": "N/A",
    "delay": "Real-time"
  }
]
```

---

### Available Sectors

Access a complete list of industry sectors using the FMP Available Sectors API. This API helps users categorize and filter companies based on their respective sectors, enabling deeper analysis and more focused queries across different industries.

The FMP Available Sectors API provides users with access to an extensive range of industry sectors, making it easier to: Categorize companies by their sector: Analyze companies within a specific industry or sector, like Technology, Healthcare, or Consumer Goods. Filter data: Use the sector filter to refine your queries and retrieve relevant data for targeted analysis. Sector-based comparisons: Compare companies within the same sector for peer analysis and benchmarking. This API is ideal for investors, analysts, and researchers who need to analyze sector-based trends or want to focus their efforts on companies operating within particular industries. Example Use Case An investment firm could use the Available Sectors API to filter and analyze companies solely within the Technology sector, enabling them to track growth trends or potential opportunities in that market segment.

**Endpoint:** `https://financialmodelingprep.com/stable/available-sectors`

**Example Response**

```json
[
  {
    "sector": "Basic Materials"
  }
]
```

---

### Available Industries

Access a comprehensive list of industries where stock symbols are available using the FMP Available Industries API. This API helps users filter and categorize companies based on their industry for more focused research and analysis.

The FMP Available Industries API provides detailed access to industry classifications, enabling users to: Categorize Companies by Their Industry: Organize companies based on their specific industry, such as Automotive, Pharmaceuticals, or Steel. Filter Data for Precision: Use the industry filter to refine your queries, ensuring you retrieve only relevant data. Industry-Based Comparisons: Compare companies within the same industry for deeper analysis and competitive benchmarking. This API is ideal for investors, analysts, and industry researchers seeking to focus on specific sectors or industries for targeted research and insights. Example Use Case A financial analyst could use the Available Industries API to filter out companies within the Steel industry, enabling them to perform a more granular analysis of competitors and market trends within that industry.

**Endpoint:** `https://financialmodelingprep.com/stable/available-industries`

**Example Response**

```json
[
  {
    "industry": "Steel"
  }
]
```

---

### Available Countries

Access a comprehensive list of countries where stock symbols are available with the FMP Available Countries API. This API enables users to filter and analyze stock symbols based on the country of origin or the primary market where the securities are traded.

The FMP Available Countries API offers users detailed access to country-based data, allowing them to: Filter by Country of Origin: Retrieve stock symbols based on the country where the companies are headquartered. Analyze Market Data by Country: Focus on stock exchanges and securities in specific countries for more localized market research. Country-Based Comparisons: Compare companies and securities from different countries for a global investment strategy. This API is ideal for investors, analysts, and researchers looking to focus on specific countries or markets for deeper analysis. Example Use Case An investor could use the Available Countries API to focus on companies traded in the United Kingdom, enabling a detailed analysis of UK-listed securities for international investment opportunities.

**Endpoint:** `https://financialmodelingprep.com/stable/available-countries`

**Example Response**

```json
[
  {
    "country": "FK"
  }
]
```

---

# Analyst

## Analyst Estimates

### Financial Estimates

Retrieve analyst financial estimates for stock symbols with the FMP Financial Estimates API. Access projected figures like revenue, earnings per share (EPS), and other key financial metrics as forecasted by industry analysts to inform your investment decisions.

The FMP Financial Estimates API is an invaluable resource for investors who want a deeper understanding of a company's projected performance. By collecting forecasts from leading financial analysts, this API provides essential insights into: Revenue Projections: Get estimates on future company revenue, offering a glimpse into anticipated growth trends. Earnings Per Share (EPS) Forecasts: Access analyst predictions on a company&rsquo;s future earnings, which are critical for evaluating profitability. Consensus Metrics: View consensus estimates from multiple analysts, providing a comprehensive outlook on the market&rsquo;s expectations. Investment Planning: Use these estimates to benchmark a company's projected performance, identify potential over- or undervalued stocks, and refine your investment strategies. The Financial Estimates API is ideal for investors, traders, and financial analysts looking to build more accurate financial models or make informed investment decisions based on market forecasts.

**Endpoint:** `https://financialmodelingprep.com/stable/analyst-estimates?symbol=AAPL&period=annual&page=0&limit=10`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| period* | string | annual,quarter |
| page | number | 0 |
| limit | number | 10 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2030-09-27",
    "revenueLow": 626395080065,
    "revenueHigh": 691467177041,
    "revenueAvg": 648898666667,
    "ebitdaLow": 226087880398,
    "ebitdaHigh": 249574674829,
    "ebitdaAvg": 234210211428,
    "ebitLow": 209796492582,
    "ebitHigh": 231590881052,
    "ebitAvg": 217333546576,
    "netIncomeLow": 183687950827,
    "netIncomeHigh": 208765000830,
    "netIncomeAvg": 192360215552,
    "sgaExpenseLow": 40316327360,
    "sgaExpenseHigh": 44504527503,
    "sgaExpenseAvg": 41764713519,
    "epsAvg": 12.82,
    "epsHigh": 13.91331,
    "epsLow": 12.24203,
    "numAnalystsRevenue": 17,
    "numAnalystsEps": 15
  }
]
```

---

## Ratings

### Ratings Snapshot

Quickly assess the financial health and performance of companies with the FMP Ratings Snapshot API. This API provides a comprehensive snapshot of financial ratings for stock symbols in our database, based on various key financial ratios.

The FMP Ratings Snapshot API allows users to evaluate a company's financial performance across multiple dimensions by delivering: Overall Rating: Get a summary score that reflects the company's financial standing. Discounted Cash Flow (DCF) Score: Understand the company&rsquo;s valuation compared to its future cash flow potential. Return on Equity (ROE) Score: Measure how efficiently a company is generating profit relative to shareholders' equity. Return on Assets (ROA) Score: Gauge how effectively a company uses its assets to generate earnings. Debt-to-Equity Score: Analyze the company&rsquo;s capital structure and risk by comparing its debt to equity. Price-to-Earnings (P/E) Score: Assess the company&rsquo;s stock price relative to its earnings to understand its valuation. Price-to-Book (P/B) Score: Compare the company&rsquo;s market price to its book value to evaluate potential investment opportunities. This API offers an overall rating, along with scores for critical metrics such as discounted cash flow, return on equity, return on assets, debt-to-equity, price-to-earnings, and price-to-book ratios. It is perfect for investors, financial analysts, and researchers who need a fast, comprehensive view of a company&rsquo;s financial health based on key metrics. Example Use Case An equity analyst can use the Ratings Snapshot API to compare multiple companies' financial health based on return on equity, debt levels, and valuation ratios, helping them make more informed investment recommendations.

**Endpoint:** `https://financialmodelingprep.com/stable/ratings-snapshot?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "rating": "B",
    "overallScore": 3,
    "discountedCashFlowScore": 3,
    "returnOnEquityScore": 5,
    "returnOnAssetsScore": 5,
    "debtToEquityScore": 1,
    "priceToEarningsScore": 2,
    "priceToBookScore": 1
  }
]
```

---

### Historical Ratings

Track changes in financial performance over time with the FMP Historical Ratings API. This API provides access to historical financial ratings for stock symbols in our database, allowing users to view ratings and key financial metric scores for specific dates.

The FMP Historical Ratings API is ideal for analysts and investors looking to assess how a company&rsquo;s financial health has evolved over time. Key features include: Historical Ratings: Retrieve ratings from past dates to track a company's financial trajectory. Overall Rating: Access an easy-to-understand rating summarizing the company&rsquo;s financial health on a given date. Discounted Cash Flow (DCF) Score: Evaluate historical valuation compared to future cash flow potential. Return on Equity (ROE) Score: Track past performance on generating profit relative to shareholders' equity. Return on Assets (ROA) Score: View how asset utilization has changed over time. Debt-to-Equity Score: Examine changes in the company&rsquo;s capital structure. Price-to-Earnings (P/E) Score: Monitor historical stock valuation relative to earnings. Price-to-Book (P/B) Score: Assess how market price has compared to book value in the past. This API is ideal for conducting trend analysis and understanding how various financial metrics have influenced a company&rsquo;s rating over time. It includes an overall rating and individual scores for critical financial ratios such as discounted cash flow, return on equity, return on assets, debt-to-equity, price-to-earnings, and price-to-book ratios. Example Use Case A portfolio manager can use the Historical Ratings API to analyze how a company&rsquo;s return on equity and debt-to-equity ratios have evolved over the last five years, helping them evaluate long-term performance trends.

**Endpoint:** `https://financialmodelingprep.com/stable/ratings-historical?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 1 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2026-06-05",
    "rating": "B",
    "overallScore": 3,
    "discountedCashFlowScore": 3,
    "returnOnEquityScore": 5,
    "returnOnAssetsScore": 5,
    "debtToEquityScore": 1,
    "priceToEarningsScore": 2,
    "priceToBookScore": 1
  }
]
```

---

## Price Targets

### Price Target Summary

Gain insights into analysts' expectations for stock prices with the FMP Price Target Summary API. This API provides access to average price targets from analysts across various timeframes, helping investors assess future stock performance based on expert opinions.

The FMP Price Target Summary API allows users to track and analyze analysts' price targets for individual stocks, making it a valuable tool for investors and analysts looking to understand market sentiment. Key features include: Average Price Targets: Access average price targets from analysts over different periods (last month, last quarter, last year, and all time). Price Target History: Track how price expectations have evolved over time to gauge changes in analysts' outlooks. Analyst Coverage: Retrieve the number of analysts providing price targets during specific periods. Multiple Publishers: View a list of sources and publishers providing price target data, such as Benzinga, MarketWatch, and Barrons. This API allows you to quickly assess the consensus among financial analysts regarding a stock&rsquo;s future price movement. Example Use Case An investor can use the Price Target Summary API to compare the average price targets for a stock over the past quarter and year to determine if analysts' outlooks have become more bullish or bearish over time.

**Endpoint:** `https://financialmodelingprep.com/stable/price-target-summary?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "lastMonthCount": 3,
    "lastMonthAvgPriceTarget": 380,
    "lastQuarterCount": 10,
    "lastQuarterAvgPriceTarget": 322.6,
    "lastYearCount": 58,
    "lastYearAvgPriceTarget": 293.43,
    "allTimeCount": 242,
    "allTimeAvgPriceTarget": 225.33,
    "publishers": "[\"TheFly\",\"StreetInsider\",\"Benzinga\",\"Pulse 2.0\",\"TipRanks Contributor\",\"MarketWatch\",\"Investing\",\"Barrons\",\"Investor's Business Daily\"]"
  }
]
```

---

### Price Target Consensus

Access analysts' consensus price targets with the FMP Price Target Consensus API. This API provides high, low, median, and consensus price targets for stocks, offering investors a comprehensive view of market expectations for future stock prices.

The FMP Price Target Consensus API delivers key insights into stock price forecasts by aggregating price targets from analysts. This allows investors to make more informed decisions based on the following metrics: High Price Target: See the highest price target forecasted by analysts. Low Price Target: Access the lowest expected price for a stock, providing insight into downside risk. Median Price Target: Get the median price target to understand the central tendency of analysts' predictions. Consensus Price Target: Retrieve the overall consensus target, which reflects the average of analysts' forecasts. This API offers a broad perspective on price expectations, helping users to evaluate the potential range of stock movements based on expert predictions. Example Use Case A portfolio manager can use the Price Target Consensus API to assess the potential upside and downside for a stock, using the high, low, median, and consensus price targets to create risk-reward scenarios for investment decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/price-target-consensus?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "targetHigh": 400,
    "targetLow": 253,
    "targetConsensus": 323.82,
    "targetMedian": 325
  }
]
```

---

## Upgrades Downgrades

### Stock Grades

Access the latest stock grades from top analysts and financial institutions with the FMP Grades API. Track grading actions, such as upgrades, downgrades, or maintained ratings, for specific stock symbols, providing valuable insight into how experts evaluate companies over time.

The FMP Grades API offers timely data on stock evaluations by prominent financial institutions, including: Grading Company: Identify the institution providing the stock rating. Previous Grade and New Grade: View the change in grade, if any, from previous assessments to the latest one. Action Taken: Determine whether the grade was upgraded, downgraded, or maintained. Date of Evaluation: See when the latest grading action occurred. This API helps investors and analysts understand the latest sentiment from financial experts, enabling better investment decisions based on how stocks are graded. Example Use Case An investor can use the Grades API to track the latest stock ratings for their portfolio, seeing how financial institutions view the company's current performance and investment potential.

**Endpoint:** `https://financialmodelingprep.com/stable/grades?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2026-05-26",
    "gradingCompany": "B of A Securities",
    "previousGrade": "Buy",
    "newGrade": "Buy",
    "action": "maintain"
  }
]
```

---

### Historical Stock Grades

Access a comprehensive record of analyst grades with the FMP Historical Grades API. This tool allows you to track historical changes in analyst ratings for specific stock symbol

The FMP Historical Grades API offers an in-depth look at how analysts have rated specific stocks in the past. This API is perfect for: Trend Analysis: Investors can use historical ratings to spot long-term trends in market sentiment for a stock, helping to predict future price movements. Investment Strategy Optimization: By tracking changes in analyst sentiment over time, investors can adjust their strategies based on whether analysts are becoming more bullish or bearish. Benchmarking Performance: Compare a stock&rsquo;s historical ratings to its actual performance, enabling a deeper understanding of how well the stock has lived up to expectations. Market Sentiment Tracking: Use the API to analyze how buy, hold, and sell ratings have changed, providing insight into broader market confidence or caution around a stock. This API empowers investors with historical context, offering a valuable tool for long-term financial analysis and decision-making. Example Use Case A portfolio manager can utilize the Historical Grades API to observe changes in analyst sentiment for a particular stock, helping them adjust their strategy based on evolving market outlooks.

**Endpoint:** `https://financialmodelingprep.com/stable/grades-historical?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2026-06-01",
    "analystRatingsStrongBuy": 7,
    "analystRatingsBuy": 23,
    "analystRatingsHold": 15,
    "analystRatingsSell": 1,
    "analystRatingsStrongSell": 2
  }
]
```

---

### Stock Grades Summary

Quickly access an overall view of analyst ratings with the FMP Grades Summary API. This API provides a consolidated summary of market sentiment for individual stock symbols, including the total number of strong buy, buy, hold, sell, and strong sell ratings. Understand the overall consensus on a stock’s outlook with just a few data points.

The FMP Grades Summary API simplifies the process of gauging market sentiment by delivering a clear breakdown of analyst ratings. It is particularly valuable for: Market Sentiment Assessment: Quickly assess the overall market opinion on a stock, whether it's leaning towards buy, hold, or sell. Investment Decision Support: Use the consensus ratings to guide your investment decisions, knowing how many analysts recommend buying or selling a stock. Portfolio Monitoring: Keep an eye on stocks in your portfolio by reviewing changes in analyst sentiment and adjusting your positions accordingly. Streamlined Stock Analysis: For users looking to get a high-level understanding of a stock's market position, the summarized data offers an efficient way to digest complex rating information. This API helps investors and analysts make informed decisions with a quick glance at how the market views a stock.

**Endpoint:** `https://financialmodelingprep.com/stable/grades-consensus?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "strongBuy": 1,
    "buy": 69,
    "hold": 33,
    "sell": 7,
    "strongSell": 0,
    "consensus": "Buy"
  }
]
```

---

# Calendar

## Dividends

### Dividends Company

Stay informed about upcoming dividend payments with the FMP Dividends Company API. This API provides essential dividend data for individual stock symbols, including record dates, payment dates, declaration dates, and more.

The FMP Dividends Company API offers a comprehensive view of the dividend information for specific stocks. Designed for dividend-focused investors, this API delivers: Dividend Schedule Overview: Get access to upcoming dividend details, including record date, payment date, and declaration date, to ensure timely information on dividend payouts. Dividend Amount: View the dividend and adjusted dividend amounts to stay informed of expected payments. Yield Data: Track the dividend yield for stocks to better assess the return on investment for dividend-focused portfolios. Payment Frequency: Understand how often dividends are paid (e.g., quarterly, annually) to align your investment strategy with the stock&rsquo;s payout schedule. With detailed dividend information such as the amount, adjusted dividend, yield, and payment frequency, investors can effectively plan around dividend schedules. This API is perfect for dividend investors who need up-to-date information to make informed decisions about their income-generating investments. Example Use Case A dividend investor can use the Dividends Company API to monitor Apple&rsquo;s upcoming dividend payment, ensuring they hold the stock through the record date to receive the payment.

**Endpoint:** `https://financialmodelingprep.com/stable/dividends?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2026-05-11",
    "recordDate": "2026-05-11",
    "paymentDate": "2026-05-14",
    "declarationDate": "2026-04-30",
    "adjDividend": 0.27,
    "dividend": 0.27,
    "yield": 0.3587535875358754,
    "frequency": "Quarterly"
  }
]
```

---

### Dividends Calendar

Stay informed on upcoming dividend events with the Dividend Events Calendar API. Access a comprehensive schedule of dividend-related dates for all stocks, including record dates, payment dates, declaration dates, and dividend yields.

The Dividend Events Calendar API provides a market-wide view of upcoming dividend events. Ideal for investors, financial analysts, and portfolio managers, this API enables: Comprehensive Dividend Calendar: View upcoming record, payment, and declaration dates for dividends across various stocks. Dividend Yield Tracking: Analyze the dividend yield to assess potential returns for each stock. Payment Frequency Details: Identify whether dividends are paid quarterly, annually, or at other intervals to plan future investments. Efficient Market Monitoring: Keep track of dividend events across the entire market to spot opportunities and trends. This API makes it easy for investors to stay ahead of dividend events and optimize their income strategies. Example Use Case A portfolio manager can use the Dividend Events Calendar API to keep track of upcoming dividend payments for all stocks in their portfolio, ensuring they don't miss important dividend events or payouts.

**Endpoint:** `https://financialmodelingprep.com/stable/dividends-calendar`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| from | date | 2026-03-06 |
| to | date | 2026-06-06 |
| page | number | 0 |

**Example Response**

```json
[
  {
    "symbol": "0W2Y.L",
    "date": "2026-06-05",
    "recordDate": "2026-06-05",
    "paymentDate": "2026-06-30",
    "declarationDate": "",
    "adjDividend": 0.42,
    "dividend": 0.42,
    "yield": 0.9676254663617764,
    "frequency": "Quarterly"
  }
]
```

---

## Earnings

### Earnings Report

Retrieve in-depth earnings information with the FMP Earnings Report API. Gain access to key financial data for a specific stock symbol, including earnings report dates, EPS estimates, and revenue projections to help you stay on top of company performance.

The Earnings Report API provides detailed insights into the earnings announcements of publicly traded companies. It&rsquo;s designed for investors and analysts who need to monitor earnings reports closely to make informed trading and investment decisions, including: Earnings Report Timing: Track earnings announcements for specific companies, including whether reports are released after market close (amc) or before market open (bmo). EPS and Revenue Estimates: Access estimated earnings per share (EPS) and revenue data ahead of earnings announcements to understand market expectations. Performance Tracking: See how actual earnings compare to estimates once they are released, helping identify trends in company performance. Market Reaction Insights: Use earnings data to predict potential stock price movements based on whether a company beats or misses earnings expectations. This API is ideal for those looking to stay updated on company earnings and monitor how these reports may impact stock prices. Example Use Case A financial analyst can use the Earnings Report API to track Apple's upcoming earnings report, reviewing EPS and revenue estimates to predict how the stock might react after the earnings are announced.

**Endpoint:** `https://financialmodelingprep.com/stable/earnings?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 100 |
| includeReportTimes | boolean | false |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2026-07-30",
    "epsActual": null,
    "epsEstimated": 1.86,
    "revenueActual": null,
    "revenueEstimated": 108393400000,
    "lastUpdated": "2026-06-06"
  }
]
```

---

### Earnings Calendar

Stay informed on upcoming and past earnings announcements with the FMP Earnings Calendar API. Access key data, including announcement dates, estimated earnings per share (EPS), and actual EPS for publicly traded companies.

The FMP Earnings Calendar API is an essential tool for investors, traders, and financial analysts who need to stay updated on the earnings announcements of publicly traded companies. This API is valuable for: Tracking Earnings Announcements: Access a comprehensive list of upcoming and past earnings announcements, including the date of the announcement, estimated EPS, and actual EPS (if available). Informed Decision-Making: Earnings announcements provide crucial insights into a company's financial performance and future outlook. Use this data to make informed trading and investment decisions. Market Analysis: Analyze the earnings performance of various companies over time to identify trends, compare performance across industries, and assess the potential impact on stock prices. This API is a powerful resource for anyone who needs to monitor earnings announcements and use this information to guide their investment strategies. Example Trading Strategy: A trader might use the Earnings Calendar API to track the earnings announcements of key technology companies. By knowing the estimated and actual EPS ahead of time, the trader can prepare to make informed trades based on how the market reacts to the earnings results.

**Endpoint:** `https://financialmodelingprep.com/stable/earnings-calendar`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| from | date | 2026-03-06 |
| to | date | 2026-06-06 |
| page | number | 0 |
| includeReportTimes | boolean | false |

**Example Response**

```json
[
  {
    "symbol": "AUC",
    "date": "2026-06-05",
    "epsActual": null,
    "epsEstimated": null,
    "revenueActual": null,
    "revenueEstimated": null,
    "lastUpdated": "2026-06-06"
  }
]
```

---

## Ipos

### IPOs Calendar

Access a comprehensive list of all upcoming initial public offerings (IPOs) with the FMP IPO Calendar API. Stay up to date on the latest companies entering the public market, with essential details on IPO dates, company names, expected pricing, and exchange listings.

The FMP IPO Calendar API provides critical information for investors and market analysts interested in tracking upcoming IPOs. This API allows users to monitor the latest companies preparing to go public, including: Upcoming IPO Dates: Stay informed on when companies are scheduled to go public, providing a clear timeline for new market entrants. Company Information: Retrieve company names and key details about their IPO plans, such as which exchange they will be listed on. Expected Pricing and Shares: View expected price ranges and the number of shares being offered (if available) to evaluate potential investment opportunities. Market Insights: Use the IPO calendar to identify emerging companies and assess the overall activity of new listings in the stock market. This API is a valuable tool for investors looking to capitalize on IPOs and track market activity related to new stock listings. Example Use Case A venture capitalist can use the IPO Calendar API to track new companies entering the stock market, evaluate pricing expectations, and identify potential investment opportunities.

**Endpoint:** `https://financialmodelingprep.com/stable/ipos-calendar`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| from | date | 2026-03-06 |
| to | date | 2026-06-06 |

**Example Response**

```json
[
  {
    "symbol": "FTRAU",
    "date": "2026-06-05",
    "daa": "2026-06-05T04:00:00.000Z",
    "company": "FutureCorp Space Acquisition 1",
    "exchange": "NYSE",
    "actions": "Expected",
    "shares": 20000000,
    "priceRange": "10.00",
    "marketCap": 200000000
  }
]
```

---

### IPOs Disclosure

Access a comprehensive list of disclosure filings for upcoming initial public offerings (IPOs) with the FMP IPO Disclosures API. Stay updated on regulatory filings, including filing dates, effectiveness dates, CIK numbers, and form types, with direct links to official SEC documents.

The FMP IPO Disclosures API provides users with timely and detailed information about regulatory filings for companies planning to go public. This API is essential for analysts, investors, and regulatory professionals who need insights into IPO filing activity. Key features include: Filing and Accepted Dates: Track when companies file IPO documents and when those filings are accepted by the SEC. Effectiveness Dates: Stay informed on the effectiveness dates, signaling when IPO filings become official. Form Types and CIK Numbers: Access key details such as the CIK number and form type (e.g., S-1, CERT) to understand the nature of the filing. Direct SEC Links: Get direct access to official SEC documents to review the details of each filing. This API is a critical tool for those monitoring the regulatory process behind IPOs and understanding the disclosures that accompany companies entering the public market. Example Use Case An institutional investor can use the IPO Disclosures API to track regulatory filings for upcoming IPOs and analyze SEC documents before making investment decisions in new market entrants.

**Endpoint:** `https://financialmodelingprep.com/stable/ipos-disclosure`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| from | date | 2026-03-06 |
| to | date | 2026-06-06 |

**Example Response**

```json
[
  {
    "symbol": "WLTG",
    "filingDate": "2026-06-05",
    "acceptedDate": "2026-06-05",
    "effectivenessDate": "2026-06-05",
    "cik": "0001771146",
    "form": "CERT",
    "url": "https://www.sec.gov/Archives/edgar/data/1771146/000135445726000537/AQLG_8A_Cert_1771146.pdf"
  }
]
```

---

### IPOs Prospectus

Access comprehensive information on IPO prospectuses with the FMP IPO Prospectus API. Get key financial details, such as public offering prices, discounts, commissions, proceeds before expenses, and more. This API also provides links to official SEC prospectuses, helping investors stay informed on companies entering the public market.

The FMP IPO Prospectus API offers detailed insights into IPO filings, providing essential information to investors, analysts, and regulatory professionals. With this API, users can access: Public Offering Prices: View the price per share and total amount raised through the IPO. Discounts and Commissions: Understand the fees and commissions deducted from the gross proceeds of the IPO. Proceeds Before Expenses: See the net proceeds the company expects to raise after expenses. Filing and IPO Dates: Track when companies file their prospectuses and their scheduled IPO dates. CIK and Form Type: Get key regulatory details, including the CIK number and the form type (e.g., 424B4). Direct SEC Links: Access the full IPO prospectus filed with the SEC for complete details on the offering. This API is an invaluable tool for anyone looking to analyze IPO financial details before making investment decisions. Example Use Case An investment advisor can use the IPO Prospectus API to review a company&rsquo;s IPO financials and prospectus filings, helping them evaluate whether to recommend the IPO to clients based on the offering's structure.

**Endpoint:** `https://financialmodelingprep.com/stable/ipos-prospectus`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| from | date | 2026-03-06 |
| to | date | 2026-06-06 |

**Example Response**

```json
[
  {
    "symbol": "AVEX",
    "acceptedDate": "2026-06-05",
    "filingDate": "2026-06-05",
    "ipoDate": "2026-04-16",
    "cik": "0002096300",
    "pricePublicPerShare": 27,
    "pricePublicTotal": 216000000,
    "discountsAndCommissionsPerShare": 1.01,
    "discountsAndCommissionsTotal": 8100000,
    "proceedsBeforeExpensesPerShare": 25.99,
    "proceedsBeforeExpensesTotal": 59091494.96,
    "form": "424B4",
    "url": "https://www.sec.gov/Archives/edgar/data/2096300/000119312526258295/d147986d424b4.htm"
  }
]
```

---

## Splits

### Stock Split Details

Access detailed information on stock splits for a specific company using the FMP Stock Split Details API. This API provides essential data, including the split date and the split ratio, helping users understand changes in a company's share structure after a stock split.

The FMP Stock Split Details API is designed to offer critical insights into a company's stock split history. With this API, users can: Split Date Information: Access the exact date of a company's stock split to understand when the changes occurred. Split Ratio Details: Retrieve the split ratio, represented by the numerator and denominator, to see how many new shares are issued for every old share. Historical Reference: Track and analyze the impact of stock splits on a company's share price and market performance. This API is ideal for investors and analysts who need to monitor stock split events and assess their effects on stock ownership and market trends. Example Use Case An investor looking to track Apple's stock split history can use the Stock Split Details API to retrieve detailed data on the company's past splits, including the date and ratio, allowing them to assess how splits have impacted stock value over time.

**Endpoint:** `https://financialmodelingprep.com/stable/splits?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2020-08-31",
    "numerator": 4,
    "denominator": 1,
    "splitType": "stock-split"
  }
]
```

---

### Stock Splits Calendar

Stay informed about upcoming stock splits with the FMP Stock Splits Calendar API. This API provides essential data on upcoming stock splits across multiple companies, including the split date and ratio, helping you track changes in share structures before they occur.

The FMP Stock&nbsp;Splits Calendar API offers timely information for investors and analysts who want to stay ahead of stock split events. This API provides: Upcoming Split Dates: Know when future stock splits are scheduled, allowing you to plan your investments around these events. Split Ratios: Access detailed split ratios, which show how many new shares (numerator) are issued for each old share (denominator). Market Insight: Use this data to evaluate how upcoming splits might impact stock prices, liquidity, and shareholder value. This API helps users monitor stock split announcements across the market, ensuring they have the information needed to make informed investment decisions. Example Use Case A portfolio manager can use the Stock&nbsp;Splits Calendar API to stay updated on upcoming stock splits, such as a 1-for-100 split scheduled for GBK.ST on February 29, 2024, to adjust their strategies accordingly.

**Endpoint:** `https://financialmodelingprep.com/stable/splits-calendar`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| from | date | 2026-03-06 |
| to | date | 2026-06-06 |
| page | number | 0 |

**Example Response**

```json
[
  {
    "symbol": "CETX",
    "date": "2026-06-05",
    "numerator": 1,
    "denominator": 10,
    "splitType": "stock-split"
  }
]
```

---

# Chart

## End Of Day

### Stock Chart Light

Access simplified stock chart data using the FMP Basic Stock Chart API. This API provides essential charting information, including date, price, and trading volume, making it ideal for tracking stock performance with minimal data and creating basic price and volume charts.

The FMP Basic Stock Chart API delivers streamlined access to stock charting data for users who need to track price movements without overwhelming complexity. This API offers: Date &amp; Price Information: Easily track daily price movements for a specific stock symbol. Volume Data: Stay informed about trading activity with volume data included for each date. Basic Charting Needs: Ideal for generating simple stock price and volume charts for historical performance analysis. This API is perfect for users and developers who want a quick, straightforward way to visualize stock data without the need for detailed technical indicators. Example Use Case A financial app can use the Basic Stock Chart API to display a minimal chart showing a stock&rsquo;s daily closing price and volume, allowing users to quickly assess its performance over time.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/light?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| from | date | 2026-01-27 |
| to | date | 2026-04-27 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2026-06-05",
    "price": 307.34,
    "volume": 65310502
  }
]
```

---

### Stock Price and Volume Data

Access full price and volume data for any stock symbol using the FMP Comprehensive Stock Price and Volume Data API. Get detailed insights, including open, high, low, close prices, trading volume, price changes, percentage changes, and volume-weighted average price (VWAP).

The FMP Comprehensive Stock Price and Volume Data API provides in-depth data on stock performance over time, making it an essential tool for analysts, traders, and investors. With this API, users can: Detailed Price Data: Access complete price information, including opening, closing, high, and low prices for each trading day. Trading Volume Insights: Retrieve data on daily trading volume to analyze liquidity and market activity. Price Changes and Percentages: Track absolute price changes and percentage shifts to evaluate price movements. VWAP (Volume-Weighted Average Price): Get the VWAP to measure the average price based on volume, helping to identify price trends and market behavior. This API is perfect for users who require detailed and accurate stock price and volume data to make informed trading and investment decisions. Example Use Case A financial analyst can use the Comprehensive Stock Price and Volume Data API to monitor Apple's daily stock performance, analyzing price changes, VWAP, and trading volume to spot trends and predict future price movements.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| from | date | 2026-01-27 |
| to | date | 2026-04-27 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2026-06-05",
    "open": 312.86,
    "high": 315.17,
    "low": 307.15,
    "close": 307.34,
    "volume": 65310502,
    "change": -5.52,
    "changePercent": -1.76,
    "vwap": 310.63
  }
]
```

---

### Unadjusted Stock Price

Access stock price and volume data without adjustments for stock splits with the FMP Unadjusted Stock Price Chart API. Get accurate insights into stock performance, including open, high, low, and close prices, along with trading volume, without split-related changes.

The FMP Unadjusted Stock Price Chart API provides unadjusted historical price data, allowing traders, analysts, and investors to view stock performance without split-related adjustments. This is useful for users who want a clear view of how stock prices moved before and after stock splits. Key features include: Unadjusted Price Data: Access historical stock prices&mdash;open, high, low, and close&mdash;without any adjustments for stock splits. Volume Data: Retrieve daily trading volume for further analysis of market activity. Pre-Split Analysis: See how stock prices performed in their original form, making it easier to analyze trends prior to a split event. Clear Historical View: For investors and analysts looking to avoid the distortions caused by stock splits, this API delivers clear and unmodified data.This API is ideal for anyone who needs accurate, split-free stock data for more precise historical analysis. Example Use Case A market researcher analyzing Apple stock performance before and after a split can use the Unadjusted Stock Price Chart API to get a clear view of stock prices without any split-related adjustments.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/non-split-adjusted?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| from | date | 2026-01-27 |
| to | date | 2026-04-27 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2026-06-05",
    "adjOpen": 312.86,
    "adjHigh": 315.17,
    "adjLow": 307.15,
    "adjClose": 307.34,
    "volume": 65310502
  }
]
```

---

### Dividend Adjusted Price Chart

Analyze stock performance with dividend adjustments using the FMP Dividend-Adjusted Price Chart API. Access end-of-day price and volume data that accounts for dividend payouts, offering a more comprehensive view of stock trends over time.

The FMP Dividend-Adjusted Price Chart API delivers EOD (end-of-day) price data that is adjusted for dividends, helping traders, analysts, and investors understand stock performance while factoring in dividend payments. This ensures a more accurate analysis of stock value changes, particularly for companies with regular dividend payouts. Features include: Dividend-Adjusted Prices: Access historical stock prices&mdash;open, high, low, and close&mdash;that have been adjusted for dividend payouts, reflecting the true stock value. Volume Data: Retrieve daily trading volume to assess market activity alongside price movements. Accurate Performance Analysis: Use dividend-adjusted data to evaluate a stock&rsquo;s performance over time with the impact of dividends factored in. Enhanced Historical Insights: Ideal for long-term investors who want a clearer picture of stock growth and performance, while including the effect of dividends. This API is a valuable tool for understanding total returns, making it easier to gauge a stock&rsquo;s historical performance by incorporating dividend impacts. Example Use Case An investor tracking the historical growth of Apple stock can use the Dividend-Adjusted Price Chart API to account for the effect of dividend payouts when analyzing stock price changes over time.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/dividend-adjusted?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| from | date | 2026-01-27 |
| to | date | 2026-04-27 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2026-06-05",
    "adjOpen": 312.86,
    "adjHigh": 315.17,
    "adjLow": 307.15,
    "adjClose": 307.34,
    "volume": 65310502
  }
]
```

---

## Intraday

### 1 Min Interval Stock Chart

Access precise intraday stock price and volume data with the FMP 1-Minute Interval Stock Chart API. Retrieve real-time or historical stock data in 1-minute intervals, including key information such as open, high, low, and close prices, and trading volume for each minute.

The FMP 1-Minute Interval Stock Chart API is designed for traders, analysts, and investors who need detailed intraday stock data for technical analysis, high-frequency trading, or algorithmic strategies. With this API, you can: Detailed Intraday Data: Get stock prices at 1-minute intervals, including open, high, low, and close prices, as well as trading volume for each minute. Real-Time and Historical Data: Access real-time minute-by-minute data or retrieve historical data using specific date ranges, allowing for long-term analysis. Customization with Date Parameters: Easily pull data for any desired time frame, including historical data going back over 30 years, by setting the "from" and "to" parameters. Intraday Charting: Perfect for building detailed intraday charts that provide deeper insights into short-term stock movements. Perfect for Day Traders: For day traders or algorithmic traders, this API offers the precision needed to identify short-term trends, fluctuations, and trading opportunities. Example Use Case A day trader can use the 1-Minute Interval Stock Chart API to track Apple&rsquo;s stock price movements throughout the trading day, enabling them to make timely buy and sell decisions based on real-time price changes and volume spikes.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1min?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |
| nonadjusted | boolean | false |

**Example Response**

```json
[
  {
    "date": "2026-06-05 15:59:00",
    "open": 307.89,
    "low": 307.35,
    "high": 307.94,
    "close": 307.55,
    "volume": 100179
  }
]
```

---

### 5 Min Interval Stock Chart

Access stock price and volume data with the FMP 5-Minute Interval Stock Chart API. Retrieve detailed stock data in 5-minute intervals, including open, high, low, and close prices, along with trading volume for each 5-minute period. This API is perfect for short-term trading analysis and building intraday charts.

The FMP 5-Minute Interval Stock Chart API provides users with valuable stock data over 5-minute intervals, allowing for better insight into intraday market activity. It's designed for investors and traders who need quick, accurate data to track short-term price movements. Key features include: Short-Term Price Analysis: Track stock price movements over short periods with 5-minute interval data, providing an ideal solution for intraday traders. Precise Trading Data: Get open, high, low, and close prices, along with trading volume, for each 5-minute period to identify patterns and trends. Intraday Charting: Build detailed intraday charts for any stock symbol, allowing for enhanced visualization of short-term price trends. Historical Data Access: Use the API to retrieve historical 5-minute interval data, providing a broader scope for price analysis and trend identification. Efficient for Active Traders: This API is perfect for day traders and active investors who need fast, reliable data to make informed trading decisions. Example Use Case A day trader can use the 5-Minute Interval Stock Chart API to monitor Apple's stock throughout the trading day, identifying short-term trends and making timely trading decisions based on price fluctuations.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/5min?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |
| nonadjusted | boolean | false |

**Example Response**

```json
[
  {
    "date": "2026-06-05 15:55:00",
    "open": 308.82,
    "low": 307.35,
    "high": 308.82,
    "close": 307.55,
    "volume": 335694
  }
]
```

---

### 15 Min Interval Stock Chart

Access stock price and volume data with the FMP 15-Minute Interval Stock Chart API. Retrieve detailed stock data in 15-minute intervals, including open, high, low, close prices, and trading volume. This API is ideal for creating intraday charts and analyzing medium-term price trends during the trading day.

The FMP 15-Minute Interval Stock Chart API is designed to provide a more balanced view of stock price movements throughout the trading day. By delivering key data at 15-minute intervals, this API offers medium-term insights for traders and investors who need to monitor stock trends in a concise but effective format. Key features include: Medium-Term Price Analysis: Monitor price fluctuations over 15-minute intervals, ideal for traders who need to identify intraday trends without analyzing every minute. Comprehensive Data Points: Access key metrics such as open, high, low, close prices, and trading volume to create detailed intraday charts. Flexible Intraday Monitoring: This API is suitable for traders and investors who need to track stock performance throughout the trading day, making it easier to spot price movements and trends. Historical Data Access: Retrieve historical 15-minute interval data to conduct in-depth analysis of past trading sessions and identify recurring patterns. Efficient Data Retrieval: Ideal for those who want a balance between fast-moving data (such as 1-minute intervals) and longer-term intraday data for smarter decision-making. Example Use Case A swing trader can use the 15-Minute Interval Stock Chart API to monitor Apple stock throughout the trading day, analyzing medium-term price movements to make strategic trade entries and exits based on significant fluctuations.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/15min?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |
| nonadjusted | boolean | false |

**Example Response**

```json
[
  {
    "date": "2026-06-05 15:45:00",
    "open": 308.1,
    "low": 307.35,
    "high": 309,
    "close": 307.55,
    "volume": 1326262
  }
]
```

---

### 30 Min Interval Stock Chart

Access stock price and volume data with the FMP 30-Minute Interval Stock Chart API. Retrieve essential stock data in 30-minute intervals, including open, high, low, close prices, and trading volume. This API is perfect for creating intraday charts and tracking medium-term price movements for more strategic trading decisions.

The FMP 30-Minute Interval Stock Chart API is designed for traders and investors seeking medium-term price insights without monitoring every minute of the trading day. By delivering key stock metrics in 30-minute intervals, it offers a well-balanced view of stock performance over time. Key features include: Efficient Medium-Term Analysis: Monitor stock price fluctuations at 30-minute intervals, providing a clear view of price movements without the noise of smaller time frames. Detailed Price Metrics: Access important data points such as open, high, low, close prices, and trading volume to build comprehensive intraday charts. Ideal for Intraday Strategies: This API supports trading strategies that rely on medium-term price movements and volume patterns, making it ideal for day traders and investors. Historical Data Availability: Retrieve historical data for 30-minute intervals, helping you analyze trends and patterns from past trading sessions. Optimized for Trend Tracking: With data available at 30-minute intervals, this API offers an efficient solution for those looking to identify key trends during the trading day. Example Use Case A day trader uses the 30-Minute Interval Stock Chart API to monitor the performance of Apple stock over the course of a trading day, identifying important price patterns and volume changes to make calculated buy and sell decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/30min?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |
| nonadjusted | boolean | false |

**Example Response**

```json
[
  {
    "date": "2026-06-05 15:30:00",
    "open": 308.9,
    "low": 307.35,
    "high": 309,
    "close": 307.55,
    "volume": 3262071
  }
]
```

---

### 1 Hour Interval Stock Chart

Track stock price movements over hourly intervals with the FMP 1-Hour Interval Stock Chart API. Access essential stock price and volume data, including open, high, low, and close prices for each hour, to analyze broader intraday trends with precision.

The FMP 1-Hour Interval Stock Chart API is perfect for traders and investors who want to monitor hourly stock price movements. By delivering key price metrics every hour, this API provides a clear and comprehensive view of intraday stock trends. Key features include: Hourly Price Data: Access open, high, low, and close prices updated every hour to stay on top of stock performance throughout the trading day. Volume Tracking: Get insights into hourly trading volumes to understand market activity and liquidity at different times of the day. Broader Timeframe Analysis: Ideal for traders who focus on medium-to-long intraday trends, the API helps visualize price movements over a broader timeframe. Historical Data: Retrieve hourly historical data to analyze past price performance and identify trends over time. Ideal for Trend and Pattern Recognition: Use this data to identify key patterns such as support, resistance, or trend reversals over hourly intervals. Example Use Case A swing trader uses the 1-Hour Interval Stock Chart API to track the hourly performance of Apple stock throughout the day, helping them make informed buy and sell decisions based on observed trends and trading volume changes.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1hour?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |
| nonadjusted | boolean | false |

**Example Response**

```json
[
  {
    "date": "2026-06-05 15:30:00",
    "open": 308.9,
    "low": 307.35,
    "high": 309,
    "close": 307.55,
    "volume": 3262071
  }
]
```

---

### 4 Hour Interval Stock Chart

Analyze stock price movements over extended intraday periods with the FMP 4-Hour Interval Stock Chart API. Access key stock price and volume data in 4-hour intervals, perfect for tracking longer intraday trends and understanding broader market movements.

The FMP 4-Hour Interval Stock Chart API provides traders and investors with essential data points over longer intraday time frames, allowing for comprehensive trend analysis. Ideal for users who want to track price movements in blocks larger than 1 hour but still within the trading day. Key features include: 4-Hour Price Intervals: Access open, high, low, and close prices, updated every 4 hours to provide a clearer view of intraday market trends. Volume Data: Understand market activity by tracking trading volumes during each 4-hour period. Ideal for Medium-Term Intraday Analysis: Longer intervals allow for deeper analysis of stock movements, helping to identify patterns and trends within a trading day. Historical Data: Retrieve past 4-hour price data to study trends and create broader price movement models. Intraday Market Strategy Support: Use the data to develop trading strategies that benefit from wider price movements and shifts within a trading session. Example Use Case A position trader uses the 4-Hour Interval Stock Chart API to monitor the longer intraday performance of Apple stock, allowing them to detect more substantial trends and price shifts without getting lost in short-term fluctuations.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/4hour?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |
| nonadjusted | boolean | false |

**Example Response**

```json
[
  {
    "date": "2026-06-05 13:30:00",
    "open": 311.5,
    "low": 307.16,
    "high": 312.81,
    "close": 307.55,
    "volume": 13535139
  }
]
```

---

# Company

## Profile

### Company Profile Data

Access detailed company profile data with the FMP Company Profile Data API. This API provides key financial and operational information for a specific stock symbol, including the company's market capitalization, stock price, industry, and much more.

The FMP Company Profile Data API offers comprehensive insights into a company's financial status and operational details. This API is ideal for analysts, traders, and investors who need an in-depth look at a company&rsquo;s core financial metrics and business information. Key features include: Stock Price and Market Cap: Get the latest stock price and market capitalization for the requested symbol. Company Details: Access information like company name, description, CEO, and industry classification Financial Metrics: Track important financial metrics like dividend yield, stock beta, and trading range to assess performance and volatility. Global Identifiers: Retrieve global financial identifiers such as CIK, ISIN, and CUSIP to ensure accurate tracking across platforms. Contact Information: Obtain contact details like the company&rsquo;s address, phone number, and website for direct reference. IPO Data: Learn about the company's IPO date, sector, and whether it&rsquo;s actively trading. Example Use Case An investor researching potential tech investments can use the Company Profile Data API to review the current financial health of Apple Inc., assess its performance, and explore key metrics like its stock range and market cap to inform buying or selling decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/profile?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "price": 262.82,
    "marketCap": 3900351299800,
    "beta": 1.086,
    "lastDividend": 1.05,
    "range": "169.21-265.29",
    "change": 3.24,
    "changePercentage": 1.24817,
    "volume": 36725325,
    "averageVolume": 44645993,
    "companyName": "Apple Inc.",
    "currency": "USD",
    "cik": "0000320193",
    "isin": "US0378331005",
    "cusip": "037833100",
    "exchangeFullName": "NASDAQ Global Select",
    "exchange": "NASDAQ",
    "industry": "Consumer Electronics",
    "website": "https://www.apple.com",
    "description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide. The company offers iPhone, a line of smartphones; Mac, a line of personal computers; iPad, a line of multi-purpose tablets; and wearables, home, and accessories comprising AirPods, Apple TV, Apple Watch, Beats products, and HomePod. It also provides AppleCare support and cloud services; and operates various platforms, including the App Store that allow customers to discov...",
    "ceo": "Timothy D. Cook",
    "sector": "Technology",
    "country": "US",
    "fullTimeEmployees": "164000",
    "phone": "(408) 996-1010",
    "address": "One Apple Park Way",
    "city": "Cupertino",
    "state": "CA",
    "zip": "95014",
    "image": "https://images.financialmodelingprep.com/symbol/AAPL.png",
    "ipoDate": "1980-12-12",
    "defaultImage": false,
    "isEtf": false,
    "isActivelyTrading": true,
    "isAdr": false,
    "isFund": false
  }
]
```

---

### Company Profile by CIK

Retrieve detailed company profile data by CIK (Central Index Key) with the FMP Company Profile by CIK API. This API allows users to search for companies using their unique CIK identifier and access a full range of company data, including stock price, market capitalization, industry, and much more.

The FMP Company Profile by CIK API provides comprehensive company information for users who want to look up firms using the CIK code. Ideal for compliance officers, analysts, and investors, this API allows access to vital company details based on their CIK number. Key features include: Company Lookup by CIK: Easily find companies using their Central Index Key for fast and accurate identification. Stock Price &amp; Market Cap: Get the most up-to-date stock price and market capitalization data for the requested company. Comprehensive Financial Data: Access essential financial metrics like beta, dividend yield, and trading range to evaluate a company's performance. Global Identifiers: Retrieve key identifiers such as CIK, ISIN, and CUSIP to streamline cross-platform tracking of companies. Company Information: Get in-depth details on the company's business operations, CEO, sector, and contact information. IPO &amp; Industry Data: View company industry, sector, and IPO details to better understand its market position. Example Use Case A compliance officer conducting a regulatory review can use the Company Profile by CIK API to quickly retrieve comprehensive data on Apple Inc. using its unique CIK number, ensuring accuracy in cross-referencing the company across different databases.

**Endpoint:** `https://financialmodelingprep.com/stable/profile-cik?cik=320193`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| cik* | string | 320193 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "price": 262.82,
    "marketCap": 3900351299800,
    "beta": 1.086,
    "lastDividend": 1.05,
    "range": "169.21-265.29",
    "change": 3.24,
    "changePercentage": 1.24817,
    "volume": 36725325,
    "averageVolume": 44645993,
    "companyName": "Apple Inc.",
    "currency": "USD",
    "cik": "0000320193",
    "isin": "US0378331005",
    "cusip": "037833100",
    "exchangeFullName": "NASDAQ Global Select",
    "exchange": "NASDAQ",
    "industry": "Consumer Electronics",
    "website": "https://www.apple.com",
    "description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide. The company offers iPhone, a line of smartphones; Mac, a line of personal computers; iPad, a line of multi-purpose tablets; and wearables, home, and accessories comprising AirPods, Apple TV, Apple Watch, Beats products, and HomePod. It also provides AppleCare support and cloud services; and operates various platforms, including the App Store that allow customers to discov...",
    "ceo": "Timothy D. Cook",
    "sector": "Technology",
    "country": "US",
    "fullTimeEmployees": "164000",
    "phone": "(408) 996-1010",
    "address": "One Apple Park Way",
    "city": "Cupertino",
    "state": "CA",
    "zip": "95014",
    "image": "https://images.financialmodelingprep.com/symbol/AAPL.png",
    "ipoDate": "1980-12-12",
    "defaultImage": false,
    "isEtf": false,
    "isActivelyTrading": true,
    "isAdr": false,
    "isFund": false
  }
]
```

---

### Company Notes

Retrieve detailed information about company-issued notes with the FMP Company Notes API. Access essential data such as CIK number, stock symbol, note title, and the exchange where the notes are listed.

The FMP Company Notes API provides crucial information on notes issued by publicly traded companies. This API is particularly valuable for investors, analysts, and financial professionals tracking corporate debt instruments. Key features include: CIK and Stock Symbol Lookup: Identify notes by the company&rsquo;s Central Index Key (CIK) and stock symbol. Note Title and Terms: Get detailed titles of company-issued notes, including specific terms like interest rates and maturity dates. Exchange Information: Learn where these notes are traded, helping you track their market activity on exchanges such as NASDAQ and NYSE. The Company Notes API is an essential tool for monitoring corporate debt instruments and understanding a company&rsquo;s financial commitments.

**Endpoint:** `https://financialmodelingprep.com/stable/company-notes?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "cik": "0000320193",
    "symbol": "AAPL",
    "title": "0.000% Notes due 2025",
    "exchange": "NASDAQ"
  }
]
```

---

### Stock Peer Comparison

Identify and compare companies within the same sector and market capitalization range using the FMP Stock Peer Comparison API. Gain insights into how a company stacks up against its peers on the same exchange.

The FMP Stock Peer Comparison API provides a curated list of companies that trade on the same exchange, belong to the same sector, and have a similar market capitalization. This API is essential for: Competitive Analysis: Use the API to compare a company&rsquo;s performance against its peers. This comparison can help you identify companies that are outperforming or underperforming within their sector. Sector-Specific Insights: By focusing on companies within the same sector and market cap range, investors can obtain a more relevant and accurate comparison, making it easier to assess relative performance and market positioning. Investment Strategy: Investors can use this information to refine their investment strategy by identifying strong performers within a sector or by finding undervalued companies that have the potential to grow. This API is a valuable resource for investors seeking to conduct in-depth competitive analysis and to make informed decisions based on how a company compares to its peers. Example Use Case Performance Benchmarking: An investor might use the Stock Peer Comparison API to compare the revenue growth and earnings per share (EPS) of a technology company to those of its peers within the same sector. This can help the investor determine whether the company is a leader in its field or if it lags behind its competitors.

**Endpoint:** `https://financialmodelingprep.com/stable/stock-peers?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "GOOGL",
    "companyName": "Alphabet Inc.",
    "price": 368.53,
    "mktCap": 4457322549079
  }
]
```

---

### Delisted Companies

Stay informed with the FMP Delisted Companies API. Access a comprehensive list of companies that have been delisted from stock exchanges to avoid trading in risky stocks and identify potential financial troubles.

The FMP Delisted Companies API provides valuable information on companies that have been removed from stock exchanges. This API is essential for investors who want to: Avoid Trading in Delisted Stocks: Identify stocks that have been delisted to prevent potential losses from trading in these securities. Understand Reasons for Delisting: Learn about the various factors that can lead to a company's delisting, such as financial difficulties, failure to comply with exchange regulations, or mergers and acquisitions. Identify Financial Troubles: Use the delisted companies list as an indicator of potential financial instability or other underlying issues within a company. This API helps investors make informed decisions by providing timely information on companies that are no longer publicly traded on exchanges.

**Endpoint:** `https://financialmodelingprep.com/stable/delisted-companies?page=0&limit=100`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| page | number | 0 |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "EDAP",
    "companyName": "Edap Tms S.a.",
    "exchange": "NASDAQ",
    "ipoDate": "1997-08-01",
    "delistedDate": "2026-06-01"
  }
]
```

---

## Employee Count

### Company Employee Count

Retrieve detailed workforce information for companies, including employee count, reporting period, and filing date. The FMP Company Employee Count API also provides direct links to official SEC documents for further verification and in-depth research.

The FMP Company Employee Count API offers users access to essential data regarding a company&rsquo;s workforce size. This API is especially valuable for analysts, investors, and HR professionals who need to understand company operations, staffing trends, and workforce management. Key features include: Employee Count: Easily retrieve the total number of employees for a company based on the most recent filing data. Period of Report: Understand the timeframe of the reported employee count by accessing the period of the report. Filing Date and Form Type: View the filing date and type of document (e.g., 10-K) to understand when and where the workforce data was disclosed. Direct SEC Links: Access the official SEC source document for transparency and additional details. This API is ideal for those analyzing company size, productivity, or workforce trends and provides a clear snapshot of company operations through its employee count. Example Use Case An equity analyst can use the Company Employee Count API to assess workforce growth at Apple Inc. over the years, comparing it to changes in the company&rsquo;s revenue and profitability.

**Endpoint:** `https://financialmodelingprep.com/stable/employee-count?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "cik": "0000320193",
    "acceptanceTime": "2025-10-31 06:01:26",
    "periodOfReport": "2025-09-27",
    "companyName": "Apple Inc.",
    "formType": "10-K",
    "filingDate": "2025-10-31",
    "employeeCount": 166000,
    "source": "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/0000320193-25-000079-index.htm"
  }
]
```

---

### Company Historical Employee Count

Access historical employee count data for a company based on specific reporting periods. The FMP Company Historical Employee Count API provides insights into how a company’s workforce has evolved over time, allowing users to analyze growth trends and operational changes.

The FMP Company Historical Employee Count API is designed for users who need to track workforce trends for a company across various reporting periods. This data is especially useful for analyzing long-term growth, staffing changes, and the relationship between workforce size and financial performance. Key features include: Historical Employee Count: Retrieve workforce size over different periods to analyze growth or decline trends. Report Periods: Gain insights into specific timeframes of employee data, tied to annual or quarterly financial reports. Filing Date and Form Type: Understand when the employee data was reported, along with the corresponding SEC form type (e.g., 10-K). Direct SEC Links: Access the original SEC filings for in-depth research and transparency. This API is ideal for HR analysts, investors, and business strategists who want to track workforce changes and assess their impact on company operations. Example Use Case A financial analyst can use the Company Historical Employee Count API to compare the employee count of Apple Inc. over a five-year period to evaluate how workforce changes correlate with revenue growth and market expansion.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-employee-count?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "cik": "0000320193",
    "acceptanceTime": "2025-10-31 06:01:26",
    "periodOfReport": "2025-09-27",
    "companyName": "Apple Inc.",
    "formType": "10-K",
    "filingDate": "2025-10-31",
    "employeeCount": 166000,
    "source": "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/0000320193-25-000079-index.htm"
  }
]
```

---

## Market Cap

### Company Market Cap

Retrieve the market capitalization for a specific company on any given date using the FMP Company Market Capitalization API. This API provides essential data to assess the size and value of a company in the stock market, helping users gauge its overall market standing.

The FMP Company Market Capitalization API delivers precise data on a company's market cap for a selected date, making it an indispensable tool for investors, analysts, and financial professionals. Key features include: Market Capitalization on Specific Dates: Retrieve accurate market cap data for companies, allowing you to track changes over time. Company Valuation Analysis: Analyze a company's size and value within the stock market based on its market capitalization. Historical and Real-Time Capabilities: Access both historical and real-time market cap data for better decision-making. This API is ideal for investors, portfolio managers, and analysts who need a quick way to assess company size and evaluate its standing within the market. Example Use Case An investor tracking Apple Inc.'s market performance can use the Company Market Capitalization API to retrieve the company's market cap on specific dates, helping them understand Apple's valuation trends and compare it with competitors.

**Endpoint:** `https://financialmodelingprep.com/stable/market-capitalization?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2025-10-24",
    "marketCap": 3900351299800
  }
]
```

---

### Batch Market Cap

Retrieve market capitalization data for multiple companies in a single request with the FMP Batch Market Capitalization API. This API allows users to compare the market size of various companies simultaneously, streamlining the analysis of company valuations.

The FMP Batch Market Capitalization API offers a fast and efficient way to gather market cap data for several companies in one batch request. Key features include: Multiple Companies in One Request: Retrieve the market capitalization for numerous companies in a single API call, saving time and effort. Compare Market Sizes: Analyze and compare the market caps of different companies to evaluate their relative size and market standing. Real-Time and Historical Market Caps: Access both current and past market capitalization data to track performance over time. This API is perfect for investors, analysts, and portfolio managers who need to compare multiple companies at once, helping to identify investment opportunities and market trends quickly. Example Use Case An analyst researching tech giants can use the Batch Market Capitalization API to retrieve market cap data for Apple, Microsoft, and Google in one request. This allows them to quickly compare these companies' market sizes and assess their positions within the industry.

**Endpoint:** `https://financialmodelingprep.com/stable/market-capitalization-batch?symbols=AAPL,MSFT,GOOG`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbols* | string | AAPL,MSFT,GOOG |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2025-10-24",
    "marketCap": 3900351299800
  }
]
```

---

### Historical Market Cap

Access historical market capitalization data for a company using the FMP Historical Market Capitalization API. This API helps track the changes in market value over time, enabling long-term assessments of a company's growth or decline.

The FMP Historical Market Capitalization API allows users to retrieve past market cap data for any company listed in the database. Key features include: Track Long-Term Performance: Retrieve historical market cap data to analyze how a company's value has evolved over time. Identify Trends: Use historical data to spot trends, whether it's consistent growth, decline, or periods of volatility. Informed Investment Decisions: Investors can use this data to evaluate a company's long-term performance and make more informed investment choices. This API is ideal for analysts, portfolio managers, and investors looking to assess a company&rsquo;s growth trajectory or historical performance in the market. Example Use Case An investor looking to evaluate Apple's historical performance can use the Historical Market Capitalization API to retrieve past market cap data. This helps them understand how Apple's valuation has changed over time, identifying periods of growth or decline and comparing it with overall market conditions.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-market-capitalization?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 100 |
| from | date | 2026-04-16 |
| to | date | 2026-07-16 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2026-06-05",
    "marketCap": 4521192070120
  }
]
```

---

## Shares Float

### Company Share Float & Liquidity

Understand the liquidity and volatility of a stock with the FMP Company Share Float and Liquidity API. Access the total number of publicly traded shares for any company to make informed investment decisions.

The FMP Company Share Float and Liquidity API provides essential data on the number of publicly traded shares for a given company, also known as the company&rsquo;s float. This endpoint helps investors: Evaluate Stock Liquidity: Identify the number of shares available for trading, which directly impacts the liquidity of the stock. Assess Volatility: Understand how the size of a company&rsquo;s float can influence stock price volatility, with smaller floats generally leading to higher volatility. Make Informed Decisions: Use float data to identify companies with large or small floats, helping to assess the potential risk and reward of investing in those companies. For example, companies with a large float tend to have more liquid stocks and less price volatility, while companies with a small float may experience higher price fluctuations due to lower liquidity.

**Endpoint:** `https://financialmodelingprep.com/stable/shares-float?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2026-06-05 08:13:10",
    "freeFloat": 99.83099999754891,
    "floatShares": 14662534368,
    "outstandingShares": 14687356000,
    "source": "https://www.sec.gov/Archives/edgar/data/320193/000032019326000013/aapl-20260328.htm"
  }
]
```

---

### All Shares Float

Access comprehensive shares float data for all available companies with the FMP All Shares Float API. Retrieve critical information such as free float, float shares, and outstanding shares to analyze liquidity across a wide range of companies.

The FMP All Shares Float API provides valuable data on the liquidity of publicly traded companies by offering insights into shares available for trading. This API is essential for investors, analysts, and financial professionals seeking to understand a company's market activity. Key features include: Free Float Data: Understand the number of shares available for public trading, excluding closely held shares owned by insiders, employees, or major shareholders. Float Shares &amp; Outstanding Shares: Retrieve the total number of shares that are both floating on the market and outstanding, helping you analyze a company's total market exposure. Comparative Liquidity Analysis: With access to free float and outstanding shares across multiple companies, you can compare liquidity, determine market stability, and evaluate investment potential. This API serves as a critical resource for evaluating the ease with which shares can be bought or sold on the open market, offering a detailed picture of company share availability and market behavior.

**Endpoint:** `https://financialmodelingprep.com/stable/shares-float-all?page=0&limit=1000`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| limit | number | 1000 |
| page | number | 0 |

**Example Response**

```json
[
  {
    "symbol": "000001.SZ",
    "date": "2026-06-06 09:23:35",
    "freeFloat": 41.40900000201062,
    "floatShares": 8035796667,
    "outstandingShares": 19405918198
  }
]
```

---

## Mergers

### Latest Mergers & Acquisitions

Access real-time data on the latest mergers and acquisitions with the FMP Latest Mergers and Acquisitions API. This API provides key information such as the transaction date, company names, and links to detailed filing information for further analysis.

The FMP Latest Mergers and Acquisitions API delivers the most recent information on corporate mergers and acquisitions, giving users access to essential data about company takeovers and transactions. Key features include: Transaction Details: Get information on the companies involved, including acquiring and targeted firms. Filing Information: Access official filings and documents from the SEC for a deeper analysis of the deal. Timely Updates: Stay informed with the most recent mergers and acquisitions data, providing insights into market consolidation. This API is ideal for analysts, investors, and corporate strategists looking to track corporate activity and make informed decisions based on the latest M&amp;A trends. Example Use Case An investment analyst can use the Latest Mergers and Acquisitions API to track recent acquisitions and evaluate the impact of these deals on the companies involved. The data can be used to assess market consolidation, competitive dynamics, and potential investment opportunities.

**Endpoint:** `https://financialmodelingprep.com/stable/mergers-acquisitions-latest?page=0&limit=100`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| page | number | 0 |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "GNL-PE",
    "companyName": "Global Net Lease, Inc.",
    "cik": "0001526113",
    "targetedCompanyName": "Modiv Industrial, Inc.",
    "targetedCik": "0001645873",
    "targetedSymbol": "MDV",
    "transactionDate": "2026-06-01",
    "acceptedDate": "2026-06-01 07:09:29",
    "link": "https://www.sec.gov/Archives/edgar/data/1526113/000110465926068543/tm2615734-1_s4.htm"
  }
]
```

---

### Search Mergers & Acquisitions

Search for specific mergers and acquisitions data with the FMP Search Mergers and Acquisitions API. Retrieve detailed information on M&A activity, including acquiring and targeted companies, transaction dates, and links to official SEC filings.

The FMP Search Mergers and Acquisitions API allows users to find mergers and acquisitions by company name, enabling a deeper understanding of corporate activity. This API is useful for those needing detailed data on past and ongoing deals, including: Company-Specific M&amp;A Data: Search for M&amp;A transactions involving specific companies, either as the acquirer or target. Transaction Dates: Access the exact dates of the transactions for precise tracking. Filing Links: Obtain links to official SEC documents for detailed information on the terms and conditions of the deal. This API is perfect for financial analysts, researchers, and corporate strategists who need comprehensive M&amp;A data to inform business or investment decisions. Example Use Case A corporate strategist can use the Search Mergers and Acquisitions API to identify past acquisition targets of a competitor. This information can help shape competitive strategies or identify industry trends that may affect future business opportunities.

**Endpoint:** `https://financialmodelingprep.com/stable/mergers-acquisitions-search?name=Apple`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| name* | string | Apple |

**Example Response**

```json
[
  {
    "symbol": "PEGY",
    "companyName": "Pineapple Energy Inc.",
    "cik": "0000022701",
    "targetedCompanyName": "Communications Systems, Inc.",
    "targetedCik": "0000022701",
    "targetedSymbol": "JCS",
    "transactionDate": "2021-11-12",
    "acceptedDate": "2021-11-12 09:54:22",
    "link": "https://www.sec.gov/Archives/edgar/data/22701/000089710121000932/a211292_s-4.htm"
  }
]
```

---

## Executive Compensation

### Company Executives

Retrieve detailed information on company executives with the FMP Company Executives API. This API provides essential data about key executives, including their name, title, compensation, and other demographic details such as gender and year of birth.

The FMP Company Executives API offers a comprehensive view of a company's leadership team, ideal for investors, researchers, and analysts who need to assess the structure and leadership of a company. This API is useful for: Executive Profiles: Access details like executive names, their roles within the company, and compensation data. Demographic Data: Get additional demographic insights, including gender and year of birth. Compensation Analysis: Analyze executive pay, which can be a key indicator of company priorities and leadership value. This API delivers a clear overview of company leadership, helping users understand who is in charge and how well they are compensated for their role. Example Use Case An investor looking to assess the leadership of a company before making a large investment can use the Company Executives API to review the backgrounds and compensation of top executives, providing insight into how leadership may impact company performance.

**Endpoint:** `https://financialmodelingprep.com/stable/key-executives?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "title": "Senior Vice President of Worldwide Marketing",
    "name": "Greg Joswiak",
    "pay": null,
    "currencyPay": "USD",
    "gender": "male",
    "yearBorn": null,
    "titleSince": null,
    "active": true
  }
]
```

---

### Executive Compensation

Retrieve comprehensive compensation data for company executives with the FMP Executive Compensation API. This API provides detailed information on salaries, stock awards, total compensation, and other relevant financial data, including filing details and links to official documents.

The FMP Executive Compensation API is designed to give investors, analysts, and researchers a complete overview of executive compensation for publicly traded companies. This API is beneficial for: Executive Salary &amp; Benefits: Retrieve data on annual salaries, stock awards, bonuses, and incentive plans. Comprehensive Compensation Breakdown: Access detailed reports on total compensation, including base pay and additional awards or incentives. Filing Information: Includes key filing dates and direct links to SEC filings for deeper analysis of compensation packages. This API provides valuable insights into how company executives are compensated, helping users understand leadership incentives and assess company governance. Example Use Case A compensation analyst can use the Executive Compensation API to compare CEO pay across different companies, analyzing how various forms of compensation&mdash;such as salary, stock awards, and performance incentives&mdash;impact executive behavior and company performance.

**Endpoint:** `https://financialmodelingprep.com/stable/governance-executive-compensation?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "cik": "0000320193",
    "symbol": "AAPL",
    "companyName": "Apple Inc.",
    "filingDate": "2026-01-08",
    "acceptedDate": "2026-01-08 16:31:36",
    "nameAndPosition": "Deirdre O’Brien Senior Vice President, Retail + People",
    "year": 2023,
    "salary": 1000000,
    "bonus": 0,
    "stockAward": 22323641,
    "optionAward": 0,
    "incentivePlanCompensation": 3571150,
    "allOtherCompensation": 42219,
    "total": 26937010,
    "link": "https://www.sec.gov/Archives/edgar/data/320193/000130817926000008/0001308179-26-000008-index.htm"
  }
]
```

---

### Executive Compensation Benchmark

Gain access to average executive compensation data across various industries with the FMP Executive Compensation Benchmark API. This API provides essential insights for comparing executive pay by industry, helping you understand compensation trends and benchmarks.

The FMP Executive Compensation Benchmark API is designed to help businesses, analysts, and compensation consultants assess how executive pay compares across industries. It&rsquo;s ideal for: Industry Benchmarking: Evaluate average executive compensation within specific industries to determine market rates. Compensation Trends: Understand how executive pay varies across different sectors, providing valuable insights for salary negotiations or organizational planning. Competitive Analysis: Compare compensation data by industry to ensure your company remains competitive in attracting top talent. This API provides a valuable resource for HR professionals, compensation analysts, and business leaders seeking to align executive pay with industry standards. Example Use Case An HR professional can use the Executive Compensation Benchmark API to compare the average pay for executives in the technology sector against those in the consumer goods sector, helping to determine competitive salary packages for their company's leadership team.

**Endpoint:** `https://financialmodelingprep.com/stable/executive-compensation-benchmark`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| year | string | 2024 |

**Example Response**

```json
[
  {
    "industryTitle": "ABRASIVE, ASBESTOS & MISC NONMETALLIC MINERAL PRODS",
    "year": 2024,
    "averageCompensation": 784407.5555555555
  }
]
```

---

# CommitmentOfTraders

## Commitment Of Traders

### COT Report

Access comprehensive Commitment of Traders (COT) reports with the FMP COT Report API. This API provides detailed information about long and short positions across various sectors, helping you assess market sentiment and track positions in commodities, indices, and financial instruments.

The FMP COT Report API is designed for traders, analysts, and market observers to evaluate the positions of market participants. This includes: Market Sentiment Tracking: Understand how commercial and non-commercial traders are positioned, giving you insights into the current sentiment of a specific market. Sector-Wide Analysis: Analyze trader positions across different sectors such as soft commodities, energy, and financials, offering a holistic view of market trends. Long and Short Positions: Get detailed data on long, short, and spread positions, helping you make informed decisions on market direction. This API is perfect for anyone looking to gain a deeper understanding of market dynamics by observing how various market participants are positioned. Example Use Case A commodity trader can use the COT Report API to analyze the open interest and trader positions in the cocoa market, identifying trends in long and short positions to refine their trading strategy.

**Endpoint:** `https://financialmodelingprep.com/stable/commitment-of-traders-report`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol | string | AAPL |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |

**Example Response**

```json
[
  {
    "symbol": "SB",
    "date": "2024-02-27 00:00:00",
    "name": "Sugar #11 (SB)",
    "sector": "SOFTS",
    "marketAndExchangeNames": "SUGAR NO. 11 - ICE FUTURES U.S.",
    "cftcContractMarketCode": "080732",
    "cftcMarketCode": "ICUS",
    "cftcRegionCode": "1",
    "cftcCommodityCode": "80",
    "openInterestAll": 822162,
    "noncommPositionsLongAll": 187869,
    "noncommPositionsShortAll": 84615,
    "noncommPositionsSpreadAll": 137056,
    "commPositionsLongAll": 431227,
    "commPositionsShortAll": 542179,
    "totReptPositionsLongAll": 756152,
    "totReptPositionsShortAll": 763850,
    "nonreptPositionsLongAll": 66010,
    "nonreptPositionsShortAll": 58312,
    "openInterestOld": 822162,
    "noncommPositionsLongOld": 187869,
    "noncommPositionsShortOld": 84615,
    "noncommPositionsSpreadOld": 137056,
    "commPositionsLongOld": 431227,
    "commPositionsShortOld": 542179,
    "totReptPositionsLongOld": 756152,
    "totReptPositionsShortOld": 763850,
    "nonreptPositionsLongOld": 66010,
    "nonreptPositionsShortOld": 58312,
    "openInterestOther": 0,
    "noncommPositionsLongOther": 0,
    "noncommPositionsShortOther": 0,
    "noncommPositionsSpreadOther": 0,
    "commPositionsLongOther": 0,
    "commPositionsShortOther": 0,
    "totReptPositionsLongOther": 0,
    "totReptPositionsShortOther": 0,
    "nonreptPositionsLongOther": 0,
    "nonreptPositionsShortOther": 0,
    "changeInOpenInterestAll": -26401,
    "changeInNoncommLongAll": 3695,
    "changeInNoncommShortAll": -7869,
    "changeInNoncommSpeadAll": 5104,
    "changeInCommLongAll": -29835,
    "changeInCommShortAll": -16576,
    "changeInTotReptLongAll": -21036,
    "changeInTotReptShortAll": -19341,
    "changeInNonreptLongAll": -5365,
    "changeInNonreptShortAll": -7060,
    "pctOfOpenInterestAll": 100,
    "pctOfOiNoncommLongAll": 22.9,
    "pctOfOiNoncommShortAll": 10.3,
    "pctOfOiNoncommSpreadAll": 16.7,
    "pctOfOiCommLongAll": 52.5,
    "pctOfOiCommShortAll": 65.9,
    "pctOfOiTotReptLongAll": 92,
    "pctOfOiTotReptShortAll": 92.9,
    "pctOfOiNonreptLongAll": 8,
    "pctOfOiNonreptShortAll": 7.1,
    "pctOfOpenInterestOl": 100,
    "pctOfOiNoncommLongOl": 22.9,
    "pctOfOiNoncommShortOl": 10.3,
    "pctOfOiNoncommSpreadOl": 16.7,
    "pctOfOiCommLongOl": 52.5,
    "pctOfOiCommShortOl": 65.9,
    "pctOfOiTotReptLongOl": 92,
    "pctOfOiTotReptShortOl": 92.9,
    "pctOfOiNonreptLongOl": 8,
    "pctOfOiNonreptShortOl": 7.1,
    "pctOfOpenInterestOther": 0,
    "pctOfOiNoncommLongOther": 0,
    "pctOfOiNoncommShortOther": 0,
    "pctOfOiNoncommSpreadOther": 0,
    "pctOfOiCommLongOther": 0,
    "pctOfOiCommShortOther": 0,
    "pctOfOiTotReptLongOther": 0,
    "pctOfOiTotReptShortOther": 0,
    "pctOfOiNonreptLongOther": 0,
    "pctOfOiNonreptShortOther": 0,
    "tradersTotAll": 216,
    "tradersNoncommLongAll": 75,
    "tradersNoncommShortAll": 45,
    "tradersNoncommSpreadAll": 70,
    "tradersCommLongAll": 79,
    "tradersCommShortAll": 71,
    "tradersTotReptLongAll": 187,
    "tradersTotReptShortAll": 156,
    "tradersTotOl": 216,
    "tradersNoncommLongOl": 75,
    "tradersNoncommShortOl": 45,
    "tradersNoncommSpeadOl": 70,
    "tradersCommLongOl": 79,
    "tradersCommShortOl": 71,
    "tradersTotReptLongOl": 187,
    "tradersTotReptShortOl": 156,
    "tradersTotOther": 0,
    "tradersNoncommLongOther": 0,
    "tradersNoncommShortOther": 0,
    "tradersNoncommSpreadOther": 0,
    "tradersCommLongOther": 0,
    "tradersCommShortOther": 0,
    "tradersTotReptLongOther": 0,
    "tradersTotReptShortOther": 0,
    "concGrossLe4TdrLongAll": 15.3,
    "concGrossLe4TdrShortAll": 24.2,
    "concGrossLe8TdrLongAll": 24.3,
    "concGrossLe8TdrShortAll": 36.7,
    "concNetLe4TdrLongAll": 8.5,
    "concNetLe4TdrShortAll": 15.2,
    "concNetLe8TdrLongAll": 14.3,
    "concNetLe8TdrShortAll": 24.7,
    "concGrossLe4TdrLongOl": 15.3,
    "concGrossLe4TdrShortOl": 24.2,
    "concGrossLe8TdrLongOl": 24.3,
    "concGrossLe8TdrShortOl": 36.7,
    "concNetLe4TdrLongOl": 8.5,
    "concNetLe4TdrShortOl": 15.2,
    "concNetLe8TdrLongOl": 14.3,
    "concNetLe8TdrShortOl": 24.7,
    "concGrossLe4TdrLongOther": 0,
    "concGrossLe4TdrShortOther": 0,
    "concGrossLe8TdrLongOther": 0,
    "concGrossLe8TdrShortOther": 0,
    "concNetLe4TdrLongOther": 0,
    "concNetLe4TdrShortOther": 0,
    "concNetLe8TdrLongOther": 0,
    "concNetLe8TdrShortOther": 0,
    "contractUnits": "(CONTRACTS OF 112,000 POUNDS)"
  }
]
```

---

### COT Analysis By Dates

Gain in-depth insights into market sentiment with the FMP COT Report Analysis API. Analyze the Commitment of Traders (COT) reports for a specific date range to evaluate market dynamics, sentiment, and potential reversals across various sectors.

The FMP COT Report Analysis API is designed for traders, analysts, and market strategists to interpret the long and short positions of traders over time, helping to track sentiment trends and potential market shifts. This API includes: Market Sentiment Evaluation: Analyze the bullish or bearish sentiment based on long and short positions, helping you gauge the current market situation. Net Position Changes: Track changes in net positions to understand whether sentiment is becoming more bullish or bearish. Historical Sentiment Comparison: Compare current market sentiment with previous periods to detect trends or potential reversal points in the market. This API enables market participants to make informed decisions by providing detailed insights into how traders are positioned in various markets and how sentiment evolves over time. Example Use Case A commodity trader can use the COT Report Analysis API to assess the bullish sentiment in the energy market by tracking changes in the net position of Brent crude oil traders, allowing them to refine their trading strategy accordingly.

**Endpoint:** `https://financialmodelingprep.com/stable/commitment-of-traders-analysis`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol | string | AAPL |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |

**Example Response**

```json
[
  {
    "symbol": "ES",
    "date": "2024-02-27 00:00:00",
    "name": "S&P 500 E-Mini (ES)",
    "sector": "INDICES",
    "exchange": "E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE",
    "currentLongMarketSituation": 36.35,
    "currentShortMarketSituation": 63.65,
    "marketSituation": "Bearish",
    "previousLongMarketSituation": 35.67,
    "previousShortMarketSituation": 64.33,
    "previousMarketSituation": "Bearish",
    "netPostion": -224223,
    "previousNetPosition": -218530,
    "changeInNetPosition": -2.61,
    "marketSentiment": " Increasing Bearish",
    "reversalTrend": false
  }
]
```

---

### COT Report List

Access a comprehensive list of available Commitment of Traders (COT) reports by commodity or futures contract using the FMP COT Report List API. This API provides an overview of different market segments, allowing users to retrieve and explore COT reports for a wide variety of commodities and financial instruments.

The COT Report List API is ideal for traders, analysts, and researchers who want to access a complete list of available COT reports for specific markets. This API includes: Comprehensive Market Coverage: Retrieve a list of all available COT reports across various commodities, from energy to agricultural products. Easy Market Segmentation: Identify the markets and futures contracts available for analysis in the Commitment of Traders report. Symbol Identification: Easily locate the symbol associated with each commodity or contract, enabling streamlined queries and in-depth analysis. This API is useful for quickly identifying which COT reports are available and for what market segments, enabling more focused and effective market research. Example Use Case A trader looking to assess market sentiment in the natural gas market can use the COT Report List API to identify the relevant futures contract and pull detailed sentiment data from the associated COT report.

**Endpoint:** `https://financialmodelingprep.com/stable/commitment-of-traders-list`

**Example Response**

```json
[
  {
    "symbol": "NG",
    "name": "Natural Gas (NG)"
  }
]
```

---

# DiscountedCashFlow

## Dcf

### DCF Valuation

Estimate the intrinsic value of a company with the FMP Discounted Cash Flow Valuation API. Calculate the DCF valuation based on expected future cash flows and discount rates.

The FMP Discounted Cash Flow (DCF) Valuation API provides investors with a powerful tool to estimate the value of an investment. DCF is a widely used valuation method that calculates the present value of a company&rsquo;s expected future cash flows. This API allows you to: Calculate DCF Valuation: Easily compute the DCF valuation by providing the company's expected future cash flows and the appropriate discount rate. Assess Investment Opportunities: Use DCF to compare the intrinsic value of different investments, helping you identify undervalued or overvalued assets. Evaluate Investment Risk: Analyze the riskiness of an investment by understanding how sensitive the DCF valuation is to changes in cash flows or discount rates. The FMP Discounted Cash Flow Valuation API simplifies the DCF calculation process, allowing users to input the necessary financial data and quickly obtain a valuation result.

**Endpoint:** `https://financialmodelingprep.com/stable/discounted-cash-flow?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2026-06-06",
    "dcf": 151.257996217859,
    "Stock Price": 307.34
  }
]
```

---

### Levered DCF

Analyze a company’s value with the FMP Levered Discounted Cash Flow (DCF) API, which incorporates the impact of debt. This API provides post-debt company valuation, offering investors a more accurate measure of a company's true worth by accounting for its debt obligations.

The Levered DCF API is designed for investors and analysts looking to assess a company&rsquo;s valuation with more precision. By factoring in debt, it delivers a realistic estimate of the company's value. Key features include: Post-Debt Valuation: Provides a clear picture of the company&rsquo;s value after considering its debt load, which is crucial for assessing the risk and return profile of an investment. DCF Value vs. Market Price: Compare the discounted cash flow valuation to the current stock price to assess whether a stock is overvalued or undervalued. Informed Investment Decisions: With a levered DCF approach, investors can make better decisions by understanding the impact of financial obligations on a company's value. This API is essential for performing deeper financial analysis and gaining a holistic view of a company&rsquo;s valuation. Example Use Case An investor evaluating whether to buy Apple shares can use the Levered DCF API to compare the company's DCF value to its current stock price. If the DCF is significantly lower than the market price, the investor might reconsider the purchase, factoring in the company&rsquo;s debt obligations.

**Endpoint:** `https://financialmodelingprep.com/stable/levered-discounted-cash-flow?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2026-06-06",
    "dcf": 144.59825927349374,
    "Stock Price": 307.34
  }
]
```

---

### Custom DCF Advanced

Run a tailored Discounted Cash Flow (DCF) analysis using the FMP Custom DCF Advanced API. With detailed inputs, this API allows users to fine-tune their assumptions and variables, offering a more personalized and precise valuation for a company.

The Custom DCF Advanced API is designed for financial analysts and investors who want to customize their DCF analysis based on their specific forecasts and assumptions. This API gives users the flexibility to modify key variables such as revenue growth, EBITDA, capital expenditures, and risk factors to achieve a tailored company valuation. Key features include: Customizable Inputs: Adjust core financial metrics such as revenue, EBITDA, and capital expenditures to fit your projections and forecasts. Advanced Financial Assumptions: Modify factors like the risk-free rate, market risk premium, tax rate, and WACC to create a more accurate valuation. Comprehensive Output: Get detailed results including equity value, free cash flow, terminal value, and equity value per share, all based on your custom inputs. This API is ideal for professional analysts or advanced users looking to customize DCF models to reflect their investment strategy or valuation assumptions. Example Use Case An equity analyst might use the Custom DCF Advanced API to adjust Apple&rsquo;s financial forecasts, input a different market risk premium, or modify the long-term growth rate. These tailored inputs allow the analyst to create a unique valuation model for the company and make more informed investment decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/custom-discounted-cash-flow?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| revenueGrowthPct | number | 0.1094119804597946 |
| ebitdaPct | number | 0.31273548388 |
| depreciationAndAmortizationPct | number | 0.0345531631720999 |
| cashAndShortTermInvestmentsPct | number | 0.2344222126801843 |
| receivablesPct | number | 0.1533770531229388 |
| inventoriesPct | number | 0.0155245674227653 |
| payablePct | number | 0.1614868903169657 |
| ebitPct | number | 0.2781823207138459 |
| capitalExpenditurePct | number | 0.0306025847141713 |
| operatingCashFlowPct | number | 0.2886333485760204 |
| sellingGeneralAndAdministrativeExpensesPct | number | 0.0662854095187211 |
| taxRate | number | 0.14919579658453103 |
| longTermGrowthRate | number | 4 |
| costOfDebt | number | 3.64 |
| costOfEquity | number | 9.51168 |
| marketRiskPremium | number | 4.72 |
| beta | number | 1.244 |
| riskFreeRate | number | 3.64 |

**Example Response**

```json
[
  {
    "year": "2030",
    "symbol": "AAPL",
    "revenue": 529528728806,
    "revenuePercentage": 4.09,
    "ebitda": 191125428209,
    "ebitdaPercentage": 36.09,
    "ebit": 177353356628,
    "ebitPercentage": 33.49,
    "depreciation": 15508463644,
    "depreciationPercentage": 2.93,
    "totalCash": 79685715467,
    "totalCashPercentage": 15.05,
    "receivables": 114078294622,
    "receivablesPercentage": 21.54,
    "inventories": 8411056160,
    "inventoriesPercentage": 1.59,
    "payable": 101862682518,
    "payablePercentage": 19.24,
    "capitalExpenditure": -14907445037,
    "capitalExpenditurePercentage": -2.82,
    "price": 262.82,
    "beta": 1.086,
    "dilutedSharesOutstanding": 15004697000,
    "costofDebt": 4.29,
    "taxRate": 15.61,
    "afterTaxCostOfDebt": 3.62,
    "riskFreeRate": 4.29,
    "marketRiskPremium": 4.72,
    "costOfEquity": 9.42,
    "totalDebt": 112377000000,
    "totalEquity": 3943534465540,
    "totalCapital": 4055911465540,
    "debtWeighting": 2.77,
    "equityWeighting": 97.23,
    "wacc": 9.25,
    "taxRateCash": 16785417,
    "ebiat": 147583856418,
    "ufcf": 145836268225,
    "sumPvUfcf": 501812484143,
    "longTermGrowthRate": 4,
    "terminalValue": 2886777996297,
    "presentTerminalValue": 1854503914553,
    "enterpriseValue": 2356316398696,
    "netDebt": 76443000000,
    "equityValue": 2279873398696,
    "equityValuePerShare": 151.94,
    "freeCashFlowT1": 151669718954
  }
]
```

---

### Custom DCF Levered

Run a tailored Discounted Cash Flow (DCF) analysis using the FMP Custom DCF Advanced API. With detailed inputs, this API allows users to fine-tune their assumptions and variables, offering a more personalized and precise valuation for a company.

The Custom DCF Advanced API is designed for financial analysts and investors who want to customize their DCF analysis based on their specific forecasts and assumptions. This API gives users the flexibility to modify key variables such as revenue growth, EBITDA, capital expenditures, and risk factors to achieve a tailored company valuation. Key features include: Customizable Inputs: Adjust core financial metrics such as revenue, EBITDA, and capital expenditures to fit your projections and forecasts. Advanced Financial Assumptions: Modify factors like the risk-free rate, market risk premium, tax rate, and WACC to create a more accurate valuation. Comprehensive Output: Get detailed results including equity value, free cash flow, terminal value, and equity value per share, all based on your custom inputs. This API is ideal for professional analysts or advanced users looking to customize DCF models to reflect their investment strategy or valuation assumptions. Example Use Case An equity analyst might use the Custom DCF Advanced API to adjust Apple&rsquo;s financial forecasts, input a different market risk premium, or modify the long-term growth rate. These tailored inputs allow the analyst to create a unique valuation model for the company and make more informed investment decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/custom-levered-discounted-cash-flow?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| revenueGrowthPct | number | 0.1094119804597946 |
| ebitdaPct | number | 0.31273548388 |
| depreciationAndAmortizationPct | number | 0.0345531631720999 |
| cashAndShortTermInvestmentsPct | number | 0.2344222126801843 |
| receivablesPct | number | 0.1533770531229388 |
| inventoriesPct | number | 0.0155245674227653 |
| payablePct | number | 0.1614868903169657 |
| ebitPct | number | 0.2781823207138459 |
| capitalExpenditurePct | number | 0.0306025847141713 |
| operatingCashFlowPct | number | 0.2886333485760204 |
| sellingGeneralAndAdministrativeExpensesPct | number | 0.0662854095187211 |
| taxRate | number | 0.14919579658453103 |
| longTermGrowthRate | number | 4 |
| costOfDebt | number | 3.64 |
| costOfEquity | number | 9.51168 |
| marketRiskPremium | number | 4.72 |
| beta | number | 1.244 |
| riskFreeRate | number | 3.64 |

**Example Response**

```json
[
  {
    "year": "2030",
    "symbol": "AAPL",
    "revenue": 529528728806,
    "revenuePercentage": 4.09,
    "capitalExpenditure": -14907445037,
    "capitalExpenditurePercentage": -2.82,
    "price": 262.82,
    "beta": 1.086,
    "dilutedSharesOutstanding": 15004697000,
    "costofDebt": 4.29,
    "taxRate": 15.61,
    "afterTaxCostOfDebt": 3.62,
    "riskFreeRate": 4.29,
    "marketRiskPremium": 4.72,
    "costOfEquity": 9.42,
    "totalDebt": 112377000000,
    "totalEquity": 3943534465540,
    "totalCapital": 4055911465540,
    "debtWeighting": 2.77,
    "equityWeighting": 97.23,
    "wacc": 9.25,
    "operatingCashFlow": 153867620418,
    "pvLfcf": 89269832852,
    "sumPvLfcf": 488842829257,
    "longTermGrowthRate": 4,
    "freeCashFlow": 138960175381,
    "terminalValue": 2750668139916,
    "presentTerminalValue": 1767065163879,
    "enterpriseValue": 2255907993136,
    "netDebt": 76443000000,
    "equityValue": 2179464993136,
    "equityValuePerShare": 145.25,
    "freeCashFlowT1": 144518582396,
    "operatingCashFlowPercentage": 29.06
  }
]
```

---

# Economics

## Economics Data

### Treasury Rates

Access latest and historical Treasury rates for all maturities with the FMP Treasury Rates API. Track key benchmarks for interest rates across the economy.

The Treasury Rates API provides latest and historical data on Treasury rates for all maturities. These rates represent the interest rates that the US government pays on its debt obligations and serve as a critical benchmark for interest rates across the economy. Investors can use this API to: Track Treasury Rates Over Time: Monitor the movement of Treasury rates and understand how they change over different periods. Identify Interest Rate Trends: Analyze trends in interest rates to gain insights into the broader economic landscape. Make Informed Investment Decisions: Use the data to inform investment strategies based on current and historical interest rate information. This API is an invaluable tool for investors, analysts, and economists who need accurate and timely information on Treasury rates.

**Endpoint:** `https://financialmodelingprep.com/stable/treasury-rates`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| from | date | 2026-01-27 |
| to | date | 2026-04-27 |

**Example Response**

```json
[
  {
    "date": "2026-06-05",
    "month1": 3.71,
    "month2": 3.71,
    "month3": 3.78,
    "month6": 3.81,
    "year1": 3.88,
    "year2": 4.17,
    "year3": 4.22,
    "year5": 4.29,
    "year7": 4.41,
    "year10": 4.55,
    "year20": 5.03,
    "year30": 5.01
  }
]
```

---

### Economics Indicators

Access real-time and historical economic data for key indicators like GDP, unemployment, and inflation with the FMP Economic Indicators API. Use this data to measure economic performance and identify growth trends.

The FMP Economic Indicators API provides comprehensive access to real-time and historical data for a wide range of economic indicators, including GDP, unemployment rates, and inflation. These indicators are essential tools for: Economic Performance Tracking: Economic indicators such as GDP, unemployment, and inflation provide a snapshot of the overall health of the economy. By tracking these indicators over time, investors and analysts can gauge economic performance and make predictions about future economic conditions. Trend Identification: Identifying trends in economic growth is crucial for making informed investment decisions. The Economic Indicators API allows users to analyze historical data and detect patterns that can indicate economic expansion or contraction. Informed Investment Decisions: Economic data is a key factor in making informed investment decisions. By understanding the current state of the economy and its trajectory, investors can better align their portfolios with economic cycles. Example Investor Use Case An investor might use the Economic Indicators API to monitor GDP growth rates over the past decade. By analyzing this data, the investor can identify periods of strong economic growth and align their investment strategy accordingly.

**Endpoint:** `https://financialmodelingprep.com/stable/economic-indicators?name=GDP`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| name* | string | GDP,realGDP,nominalPotentialGDP,realGDPPerCapita,federalFunds,CPI,inflationRate,inflation,retailSales,consumerSentiment,durableGoods,unemploymentRate,totalNonfarmPayroll,initialClaims,industrialProductionTotalIndex,newPrivatelyOwnedHousingUnitsStartedTotalUnits,totalVehicleSales,retailMoneyFunds,smoothedUSRecessionProbabilities,3MonthOr90DayRatesAndYieldsCertificatesOfDeposit,commercialBankInterestRateOnCreditCardPlansAllAccounts,30YearFixedRateMortgageAverage,15YearFixedRateMortgageAverage,tradeBalanceGoodsAndServices |
| from | date | 2025-04-27 |
| to | date | 2026-04-27 |

**Example Response**

```json
[
  {
    "name": "GDP",
    "date": "2026-01-01",
    "value": 31819.464
  }
]
```

---

### Economic Data Releases Calendar

Stay informed with the FMP Economic Data Releases Calendar API. Access a comprehensive calendar of upcoming economic data releases to prepare for market impacts and make informed investment decisions.

The FMP Economic Data Releases Calendar API provides a detailed schedule of upcoming economic data releases. This tool is essential for investors who want to: Stay Updated on Economic Events: Access a calendar that lists the dates and details of key economic data releases. Prepare for Market Reactions: Anticipate market movements by staying informed about upcoming economic indicators and reports. Make Informed Investment Decisions: Use the latest economic data to guide your investment strategies and decisions. This API is ideal for traders, analysts, and investors who need to stay ahead of market trends by monitoring critical economic data releases.

**Endpoint:** `https://financialmodelingprep.com/stable/economic-calendar`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| country | string | US |
| from | date | 2026-01-27 |
| to | date | 2026-04-27 |

**Example Response**

```json
[
  {
    "date": "2026-06-06 16:00:00",
    "country": "US",
    "event": "Fed Barr Speech",
    "currency": "USD",
    "previous": null,
    "estimate": null,
    "actual": null,
    "change": null,
    "impact": "Medium",
    "changePercentage": 0,
    "unit": null
  }
]
```

---

### Market Risk Premium

Access the market risk premium for specific dates with the FMP Market Risk Premium API. Use this key financial metric to assess the additional return expected from investing in the stock market over a risk-free investment.

The FMP Market Risk Premium API provides the market risk premium, a critical measure in financial analysis and investment decision-making. This metric represents the difference between the expected return of the stock market and the risk-free rate, and it is essential for: Investment Valuation: The market risk premium is a fundamental component in calculating the cost of equity and assessing the value of investments. By knowing the premium, investors can evaluate whether the potential return on an investment justifies the risk. Risk Assessment: Understanding the market risk premium helps investors gauge the level of risk they are taking on compared to the risk-free rate. This can inform decisions on asset allocation and portfolio management. Financial Modeling: The market risk premium is often used in models such as the Capital Asset Pricing Model (CAPM) to estimate the expected return on an investment. Accurate market risk premium data is crucial for reliable financial modeling. Analyst Use Case An analyst might use the Market Risk Premium API to calculate the expected return on a stock investment. By subtracting the risk-free rate from the expected market return, they can determine whether the investment offers a sufficient premium to justify the associated risk.

**Endpoint:** `https://financialmodelingprep.com/stable/market-risk-premium`

**Example Response**

```json
[
  {
    "country": "Zimbabwe",
    "continent": "Africa",
    "countryRiskPremium": 11.66,
    "totalEquityRiskPremium": 15.89
  }
]
```

---

# ESG

## Esg

### ESG Investment Search

Align your investments with your values using the FMP ESG Investment Search API. Discover companies and funds based on Environmental, Social, and Governance (ESG) scores, performance, controversies, and business involvement criteria.

The FMP ESG Investment Search API is designed to help investors find companies and funds that align with their Environmental, Social, and Governance (ESG) values. This powerful tool allows you to: Search by ESG Scores: Identify companies and funds with strong ESG ratings that meet your investment criteria. Evaluate Performance: Filter investments based on their ESG performance to ensure they align with your values and financial goals. Assess Controversies: Avoid investments in companies involved in significant ESG controversies by filtering based on controversy scores. Apply Business Involvement Screens: Screen companies and funds based on specific business activities or sectors that align with your ESG principles. Examples Use Cases An investor focused on sustainability might search for companies with an ESG scores of 80 or higher to ensure strong environmental and social practices. An investor concerned about environmental impact could search for companies with low ESG controversy scores to avoid potential risks.

**Endpoint:** `https://financialmodelingprep.com/stable/esg-disclosures?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "date": "2026-03-28",
    "acceptedDate": "2026-04-30",
    "symbol": "AAPL",
    "cik": "0000320193",
    "companyName": "Apple Inc.",
    "formType": "8-K",
    "environmentalScore": 66.29,
    "socialScore": 45.21,
    "governanceScore": 58.87,
    "ESGScore": 56.79,
    "url": "https://www.sec.gov/Archives/edgar/data/320193/000032019326000011/0000320193-26-000011-index.htm"
  }
]
```

---

### ESG Ratings

Access comprehensive ESG ratings for companies and funds with the FMP ESG Ratings API. Make informed investment decisions based on environmental, social, and governance (ESG) performance data.

The FMP ESG Ratings API provides detailed ESG ratings for companies and funds, helping investors and analysts assess the sustainability and ethical impact of their investments. This API is essential for: Evaluating ESG Performance: Access ESG ratings that reflect a company&rsquo;s or fund&rsquo;s performance across environmental, social, and governance criteria, sourced from corporate sustainability reports, ESG research firms, and government agencies. Informed Investment Decisions: Use ESG ratings to identify companies and funds that align with your ethical and sustainability goals, ensuring that your investments support positive social and environmental outcomes. Filtering Based on ESG Scores: Customize your search to filter for companies with high ESG ratings or low ESG controversy scores, helping you focus on organizations that meet your specific ESG criteria. This API is a valuable tool for socially conscious investors, financial analysts, and asset managers who prioritize ESG factors in their investment strategies. Examples Use Cases High ESG Performance: An investor interested in companies with strong ESG practices can filter for those with an ESG rating of 80 or higher, ensuring that their investments align with their values. Low ESG Controversy: An analyst focused on minimizing environmental risks in their portfolio may filter for companies with low ESG controversy scores, indicating fewer issues related to environmental or social impacts.

**Endpoint:** `https://financialmodelingprep.com/stable/esg-ratings?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "cik": "0000320193",
    "companyName": "Apple Inc.",
    "industry": "CONSUMER ELECTRONICS",
    "fiscalYear": 2001,
    "ESGRiskRating": "B",
    "industryRank": "4 out of 6"
  }
]
```

---

### ESG Benchmark Comparison

Evaluate the ESG performance of companies and funds with the FMP ESG Benchmark Comparison API. Compare ESG leaders and laggards within industries to make informed and responsible investment decisions.

The FMP ESG Benchmark Comparison API allows investors and analysts to compare the Environmental, Social, and Governance (ESG) performance of companies and funds against their peers. This powerful tool helps you: Identify ESG Leaders: Find companies and funds that excel in ESG performance by comparing them to industry peers. Spot ESG Laggards: Identify companies that fall behind in ESG performance, allowing you to make informed decisions about where to allocate your investments. Monitor ESG Improvements: Track companies that are making significant strides in their ESG ratings, signaling positive change and potential investment opportunities. Example Use Cases For Investors: Filter for companies in the top 10% of their industry in ESG ratings to focus on industry leaders in sustainable practices. For Analysts: Search for companies that have shown a significant increase in their ESG rating over the past year to identify those making notable improvements in their ESG performance.

**Endpoint:** `https://financialmodelingprep.com/stable/esg-benchmark`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| year | string | 2023 |

**Example Response**

```json
[
  {
    "fiscalYear": 2023,
    "sector": "APPAREL RETAIL",
    "environmentalScore": 61.36,
    "socialScore": 67.44,
    "governanceScore": 68.1,
    "ESGScore": 65.63
  }
]
```

---

# EtfAndMutualFunds

## Holdings

### ETF & Fund Holdings

Get a detailed breakdown of the assets held within ETFs and mutual funds using the FMP ETF & Fund Holdings API. Access real-time data on the specific securities and their weights in the portfolio, providing insights into asset composition and fund strategies.

The FMP ETF &amp; Fund Holdings API offers comprehensive information about the underlying assets that make up ETFs and mutual funds. This API is crucial for investors and analysts who need: Detailed Portfolio Insights: Gain visibility into the specific assets held within an ETF or mutual fund, including information such as asset names, symbols, ISINs, market values, and weight percentages. This helps investors understand a fund&rsquo;s exposure to particular stocks, sectors, or markets. Real-Time Updates: Stay informed with up-to-date information on fund holdings. The API provides real-time updates, ensuring that you always have access to the most current data on fund compositions. Investment Strategy Analysis: Use the holdings data to evaluate the investment strategy of different ETFs and mutual funds. By analyzing the securities and their respective weightings, you can make informed decisions about potential risks and opportunities. For example, an investor interested in the SPY ETF can use this API to view Apple Inc.'s (AAPL) share count, market value, and its percentage weight in the fund, helping to assess the exposure to the tech sector.

**Endpoint:** `https://financialmodelingprep.com/stable/etf/holdings?symbol=SPY`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | SPY |

**Example Response**

```json
[
  {
    "symbol": "SPY",
    "asset": "NVDA",
    "name": "NVIDIA CORP",
    "isin": "US67066G1040",
    "securityCusip": "67066G104",
    "sharesNumber": 294624332,
    "weightPercentage": 8.16350993,
    "marketValue": 64429253531,
    "updatedAt": "2026-06-06 05:06:19"
  }
]
```

---

### ETF & Mutual Fund Information

Access comprehensive data on ETFs and mutual funds with the FMP ETF & Mutual Fund Information API. Retrieve essential details such as ticker symbol, fund name, expense ratio, assets under management, and more.

The FMP ETF &amp; Mutual Fund Information API offers a detailed look into the financial and structural information of ETFs and mutual funds. This API enables investors to: Compare Funds: Evaluate different ETFs and mutual funds by reviewing key metrics like ticker symbol, name, expense ratio, and assets under management to choose the most cost-effective and suitable investment options. Identify Investment Opportunities: Use the detailed data to discover ETFs and mutual funds that align with your specific investment strategy, risk tolerance, and financial goals. Understand Investment Objectives: Learn more about the objectives and strategies of various ETFs and mutual funds, helping you assess their suitability for inclusion in your portfolio based on asset class, sector exposure, and expense ratios. For example, an investor can use this API to compare the expense ratios of various ETFs and mutual funds, find funds with large assets under management, or analyze sector weightings to ensure their investments align with their market outlook.

**Endpoint:** `https://financialmodelingprep.com/stable/etf/info?symbol=SPY`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | SPY |

**Example Response**

```json
[
  {
    "symbol": "SPY",
    "name": "State Street SPDR S&P 500 ETF Trust",
    "description": "The State Street SPDR S&P 500 ETF Trust seeks to provide investment results that, before expenses, correspond generally to the price and yield performance of the S&P 500 Index (the “Index”)The S&P 500 Index is a diversified large cap U.S. index that holds companies across all eleven GICS sectorsLaunched in January 1993, SPY was the very first exchange traded fund listed in the United States",
    "isin": "US78462F1030",
    "assetClass": "Equity",
    "securityCusip": "78462F103",
    "domicile": "US",
    "website": "https://www.ssga.com/us/en/institutional/etfs/state-street-spdr-sp-500-etf-trust-spy",
    "etfCompany": "SPDR",
    "expenseRatio": 0.09,
    "assetsUnderManagement": 789870290000,
    "avgVolume": 73651172,
    "inceptionDate": "1993-01-22",
    "nav": 756.92,
    "navCurrency": "USD",
    "holdingsCount": 504,
    "isActivelyTrading": true,
    "updatedAt": "2026-06-06T07:46:00.054Z",
    "sectorsList": [
      {
        "industry": "Basic Materials",
        "exposure": 1.8
      },
      {
        "industry": "Communication Services",
        "exposure": 11.35
      },
      {
        "industry": "Consumer Cyclical",
        "exposure": 10.25
      }
    ]
  }
]
```

---

### ETF & Fund Country Allocation

Gain insight into how ETFs and mutual funds distribute assets across different countries with the FMP ETF & Fund Country Allocation API. This tool provides detailed information on the percentage of assets allocated to various regions, helping you make informed investment decisions.

The FMP ETF &amp; Fund Country Allocation API delivers a detailed breakdown of how ETFs and mutual funds allocate their assets by country. This data is essential for investors aiming to: Assess Geographic Exposure: Understand how assets are distributed globally, offering insights into the geographic risk and opportunities associated with different funds. Identify Country-Specific Investment Opportunities: Evaluate funds with significant exposure to countries that show strong economic growth potential, like the United States, China, or emerging markets. Diversify Your Portfolio: Use country allocation data to balance your investments across international markets, reducing concentration risk in any single region. For example, if you're looking to invest in a fund that heavily allocates its assets to the United States, you can use this API to find ETFs or mutual funds with a high percentage of their holdings in the U.S. Alternatively, if you want to diversify into international markets, this API will help you locate funds with significant exposure to foreign economies. Example Use Case An investor seeking to minimize risk by diversifying internationally might use the ETF &amp; Fund Country Allocation API to identify funds with strong exposure to emerging markets or regions like Asia or Europe.

**Endpoint:** `https://financialmodelingprep.com/stable/etf/country-weightings?symbol=SPY`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | SPY |

**Example Response**

```json
[
  {
    "country": "United States",
    "weightPercentage": "97.82%"
  }
]
```

---

### ETF Asset Exposure

Discover which ETFs hold specific stocks with the FMP ETF Asset Exposure API. Access detailed information on market value, share numbers, and weight percentages for assets within ETFs.

The FMP ETF Asset Exposure API provides detailed data on the exposure of individual stocks within various ETFs. This API is essential for: Identifying ETF Holdings: Find out which ETFs hold a particular stock, along with details such as market value, the number of shares held, and the weight percentage of the stock within the ETF. Analyzing Asset Exposure: Use the data to analyze the exposure of specific assets within ETFs, helping you understand how widely a stock is held and its significance within different funds. Informed Investment Decisions: Investors can leverage this information to assess the popularity and weight of a stock across multiple ETFs, guiding their decisions on buying or selling the stock based on its representation in the market. This API is a valuable resource for investors who want to explore the relationship between stocks and ETFs, particularly for understanding the broader market sentiment towards a specific asset. Example Use Cases ETF Research: An investor interested in Apple Inc. (AAPL) can use the ETF Asset Exposure API to find all ETFs that hold AAPL shares. The investor can then analyze the weight of AAPL within each ETF to determine which funds are most heavily invested in the stock.

**Endpoint:** `https://financialmodelingprep.com/stable/etf/asset-exposure?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "ZPDT.DE",
    "asset": "AAPL",
    "sharesNumber": 1170753,
    "weightPercentage": 17.56283,
    "marketValue": 316188722.3272
  }
]
```

---

## Holding

### ETF Sector Weighting

The FMP ETF Sector Weighting API provides a breakdown of the percentage of an ETF's assets that are invested in each sector. For example, an investor may want to invest in an ETF that has a high exposure to the technology sector if they believe that the technology sector is poised for growth.

The FMP ETF Sector Allocation API provides crucial information about the distribution of an ETF&rsquo;s assets across different sectors. This API is particularly useful for investors who want to: Analyze Sector Exposure: Gain insights into how an ETF&rsquo;s assets are allocated across sectors, such as technology, healthcare, or consumer staples, to understand its risk profile. Identify Sector-Focused ETFs: Find ETFs with significant exposure to sectors that align with your investment thesis. For instance, you might choose an ETF with a high allocation to the technology sector if you expect strong growth in that area. Diversify Portfolios: Use sector weighting data to diversify your portfolio by selecting ETFs that provide exposure to sectors where you might be under-invested, helping to balance overall risk. For example, an investor who already has significant exposure to technology stocks might seek out an ETF with substantial holdings in healthcare or consumer staples to diversify their investments and mitigate sector-specific risks.

**Endpoint:** `https://financialmodelingprep.com/stable/etf/sector-weightings?symbol=SPY`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | SPY |

**Example Response**

```json
[
  {
    "symbol": "SPY",
    "sector": "Basic Materials",
    "weightPercentage": 1.8
  }
]
```

---

## Fund Disclosures

### Mutual Fund & ETF Disclosure

Access the latest disclosures from mutual funds and ETFs with the FMP Mutual Fund & ETF Disclosure API. This API provides updates on filings, changes in holdings, and other critical disclosure data for mutual funds and ETFs.

The FMP Mutual Fund &amp; ETF Disclosure API delivers up-to-date information on the holdings and strategy changes of mutual funds and ETFs. This API is designed for investors, analysts, and financial professionals who need to: Track Fund Holdings: Stay informed on the latest holdings disclosed by mutual funds and ETFs, including the number of shares held and the percentage of the portfolio they represent. Monitor Strategy Changes: Detect changes in fund strategy by reviewing updated disclosures, which may reveal shifts in investment focus or portfolio rebalancing. Gain Insight into Major Funds: Understand the investment decisions of significant institutional players, such as Vanguard or BlackRock, by accessing their most recent filings. For example, an investor might use this API to track the latest disclosure from Vanguard&rsquo;s mutual fund, analyzing whether the fund increased or decreased its position in a particular stock, and use that information to support their own investment strategy.

**Endpoint:** `https://financialmodelingprep.com/stable/funds/disclosure-holders-latest?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "cik": "0000071958",
    "holder": "NICHOLAS FUND, INC.",
    "securityCusip": "037833100",
    "shares": 659910,
    "dateReported": "2026-04-30",
    "change": 0,
    "weightPercent": 0.56338049
  }
]
```

---

### Mutual Fund Disclosures

Access comprehensive disclosure data for mutual funds with the FMP Mutual Fund Disclosures API. Analyze recent filings, balance sheets, and financial reports to gain insights into mutual fund portfolios.

The FMP Mutual Fund Disclosures API provides detailed information on mutual fund holdings and recent filings, allowing investors and financial professionals to: Track Fund Holdings: Review the most recent disclosures of mutual fund holdings, including asset categories, issuer information, and country of investment. This helps users understand the portfolio composition of various mutual funds. Analyze Recent Filings: Obtain critical financial reports and filings from mutual funds, including balance data, market value in USD, percentage of total portfolio value, and more. These insights can help with investment analysis and strategy development. Gain Transparency into Investments: The API provides essential details like CUSIP, ISIN, issuer category, and fair value levels, offering full transparency into mutual fund investments. For example, an investor can use this API to review the holdings of a mutual fund, such as Realty Income Corp, analyzing the balance, value in USD, and percentage of portfolio allocation to help make informed investment decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/funds/disclosure?symbol=VWO&year=2023&quarter=4`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | VWO |
| year* | string | 2023 |
| quarter* | string | 4 |
| cik | string | 0000857489 |

**Example Response**

```json
[
  {
    "cik": "0000857489",
    "date": "2023-10-31",
    "acceptedDate": "2023-12-28 09:26:13",
    "symbol": "000089.SZ",
    "name": "Shenzhen Airport Co Ltd",
    "lei": "3003009W045RIKRBZI44",
    "title": "SHENZ AIRPORT-A",
    "cusip": "N/A",
    "isin": "CNE000000VK1",
    "balance": 2438784,
    "units": "NS",
    "cur_cd": "CNY",
    "valUsd": 2255873.6,
    "pctVal": 0.0023838966190458206,
    "payoffProfile": "Long",
    "assetCat": "EC",
    "issuerCat": "CORP",
    "invCountry": "CN",
    "isRestrictedSec": "N",
    "fairValLevel": "2",
    "isCashCollateral": "N",
    "isNonCashCollateral": "N",
    "isLoanByFund": "N"
  }
]
```

---

### Mutual Fund & ETF Disclosure Name Search

Easily search for mutual fund and ETF disclosures by name using the Mutual Fund & ETF Disclosure Name Search API. This API allows you to find specific reports and filings based on the fund or ETF name, providing essential details like CIK number, entity information, and reporting file number.

The Mutual Fund &amp; ETF Disclosure Name Search API helps users quickly locate disclosure documents for mutual funds and ETFs by searching with a specific fund name. It returns critical data such as the fund's symbol, CIK, class information, and the address of the reporting entity. Ideal for investors, analysts, and researchers looking for detailed disclosure information for compliance, research, or investment decision-making. Fund Name Search: Look up disclosures for mutual funds and ETFs using the fund or entity name. Key Filing Details: Get important information like CIK number, series and class IDs, entity name, and reporting file number. Comprehensive Results: The API returns address details and filing information for the searched fund or ETF entity, making it easy to locate relevant documents. This API is perfect for anyone conducting due diligence or research on mutual funds and ETFs, allowing for precise and efficient disclosure searches. Example Use Case A financial analyst can use the Mutual Fund &amp; ETF Disclosure Name Search API to retrieve specific disclosures for a mutual fund by entering its name, helping the analyst review relevant regulatory filings and reports for the fund.

**Endpoint:** `https://financialmodelingprep.com/stable/funds/disclosure-holders-search?name=Federated Hermes Government Income Securities, Inc.`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| name* | string | Federated Hermes Government Income Securities, Inc. |

**Example Response**

```json
[
  {
    "symbol": "FGOAX",
    "cik": "0000355691",
    "classId": "C000024574",
    "seriesId": "S000009042",
    "entityName": "Federated Hermes Government Income Securities, Inc.",
    "entityOrgType": "30",
    "seriesName": "Federated Hermes Government Income Securities, Inc.",
    "className": "Class A Shares",
    "reportingFileNumber": "811-03266",
    "address": "4000 ERICSSON DRIVE",
    "city": "WARRENDALE",
    "zipCode": "15086-7561",
    "state": "PA"
  }
]
```

---

### Fund & ETF Disclosures by Date

Retrieve detailed disclosures for mutual funds and ETFs based on filing dates with the FMP Fund & ETF Disclosures by Date API. Stay current with the latest filings and track regulatory updates effectively.

The FMP Fund &amp; ETF Disclosures by Date API allows users to quickly access mutual fund and ETF disclosures by specifying filing dates. This API is essential for: Tracking Recent Filings: Stay informed about the latest mutual fund and ETF filings by retrieving disclosures based on specific filing dates. This feature is ideal for analysts, investors, and compliance officers looking to stay updated on current regulatory filings. Historical Research: The API allows users to retrieve disclosures from past quarters or years, making it a valuable tool for historical financial research, performance tracking, and compliance verification. Monitoring Filing Trends: Regularly reviewing filings by date helps users keep an eye on market trends and understand how recent filings may impact the financial markets. For example, an investor may want to track all disclosures filed in the second quarter of 2024. By using the Fund &amp; ETF Disclosures by Date API, they can quickly retrieve and review these filings to understand any significant changes in fund strategies or holdings.

**Endpoint:** `https://financialmodelingprep.com/stable/funds/disclosure-dates?symbol=VWO`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | VWO |
| cik | string | 0000036405 |

**Example Response**

```json
[
  {
    "date": "2026-01-31",
    "year": 2026,
    "quarter": 1
  }
]
```

---

# Statements

## Financial Statements

### Income Statement

Access detailed income statement data for publicly traded companies with the Income Statements API. Track profitability, compare competitors, and identify business trends with up-to-date financial data.

The FMP Income Statements API provides comprehensive access to income statement data for a wide range of companies. This API is essential for: Profitability Tracking: Monitor a company's revenue, expenses, and net income over time. The income statement, also known as the profit and loss statement, provides a detailed view of a company's financial performance during a specific period. Competitive Analysis: Use the API to compare a company's financial performance to its competitors. By analyzing income statements across companies, investors can identify which businesses are leading in profitability and efficiency. Trend Identification: Detect trends in a company's business by examining changes in revenue, expenses, and net income over multiple periods. This data is crucial for understanding a company's financial health and growth prospects. Example Financial Ratio Calculation: An investor can use the Income Statements API to calculate key financial ratios, such as the price-to-earnings ratio (P/E ratio) and gross margin. These ratios help investors assess a company's valuation and profitability, enabling more informed investment decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/income-statement?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |
| period | string | Q1,Q2,Q3,Q4,FY,annual,quarter |

**Example Response**

```json
[
  {
    "date": "2024-09-28",
    "symbol": "AAPL",
    "reportedCurrency": "USD",
    "cik": "0000320193",
    "filingDate": "2024-11-01",
    "acceptedDate": "2024-11-01 06:01:36",
    "fiscalYear": "2024",
    "period": "FY",
    "revenue": 391035000000,
    "costOfRevenue": 210352000000,
    "grossProfit": 180683000000,
    "researchAndDevelopmentExpenses": 31370000000,
    "generalAndAdministrativeExpenses": 0,
    "sellingAndMarketingExpenses": 0,
    "sellingGeneralAndAdministrativeExpenses": 26097000000,
    "otherExpenses": 0,
    "operatingExpenses": 57467000000,
    "costAndExpenses": 267819000000,
    "netInterestIncome": 0,
    "interestIncome": 0,
    "interestExpense": 0,
    "depreciationAndAmortization": 11445000000,
    "ebitda": 134661000000,
    "ebit": 123216000000,
    "nonOperatingIncomeExcludingInterest": 0,
    "operatingIncome": 123216000000,
    "totalOtherIncomeExpensesNet": 269000000,
    "incomeBeforeTax": 123485000000,
    "incomeTaxExpense": 29749000000,
    "netIncomeFromContinuingOperations": 93736000000,
    "netIncomeFromDiscontinuedOperations": 0,
    "otherAdjustmentsToNetIncome": 0,
    "netIncome": 93736000000,
    "netIncomeDeductions": 0,
    "bottomLineNetIncome": 93736000000,
    "eps": 6.11,
    "epsDiluted": 6.08,
    "weightedAverageShsOut": 15343783000,
    "weightedAverageShsOutDil": 15408095000
  }
]
```

---

### Balance Sheet Statement

Access detailed balance sheet statements for publicly traded companies with the Balance Sheet Data API. Analyze assets, liabilities, and shareholder equity to gain insights into a company's financial health.

The Balance Sheet Data API allows investors, analysts, and financial professionals to retrieve detailed balance sheet information for companies. This API is essential for: Comprehensive Financial Analysis: View key data on assets, liabilities, and shareholder equity, allowing for a detailed assessment of a company's financial structure and solvency. Evaluating Company Health: Determine a company's liquidity and leverage through short-term and long-term assets, liabilities, and shareholder equity positions. Supporting Investment Decisions: Use the balance sheet to compare companies within the same industry or sector, ensuring you make informed investment decisions based on a company's financial stability. This API provides real-time and historical balance sheet data, offering a snapshot of a company's financial health over different periods. Whether you're analyzing a company's financial performance or conducting due diligence, this data helps you evaluate critical financial metrics with ease. Example Use Case An investor analyzing a potential stock purchase uses the Balance Sheet Data API to evaluate the company's assets and liabilities. They review how much cash the company has on hand, its debt obligations, and total equity to ensure the company is financially stable. &nbsp;

**Endpoint:** `https://financialmodelingprep.com/stable/balance-sheet-statement?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |
| period | string | Q1,Q2,Q3,Q4,FY,annual,quarter |

**Example Response**

```json
[
  {
    "date": "2024-09-28",
    "symbol": "AAPL",
    "reportedCurrency": "USD",
    "cik": "0000320193",
    "filingDate": "2024-11-01",
    "acceptedDate": "2024-11-01 06:01:36",
    "fiscalYear": "2024",
    "period": "FY",
    "cashAndCashEquivalents": 29943000000,
    "shortTermInvestments": 35228000000,
    "cashAndShortTermInvestments": 65171000000,
    "netReceivables": 66243000000,
    "accountsReceivables": 33410000000,
    "otherReceivables": 32833000000,
    "inventory": 7286000000,
    "prepaids": 0,
    "otherCurrentAssets": 14287000000,
    "totalCurrentAssets": 152987000000,
    "propertyPlantEquipmentNet": 45680000000,
    "goodwill": 0,
    "intangibleAssets": 0,
    "goodwillAndIntangibleAssets": 0,
    "longTermInvestments": 91479000000,
    "taxAssets": 19499000000,
    "otherNonCurrentAssets": 55335000000,
    "totalNonCurrentAssets": 211993000000,
    "otherAssets": 0,
    "totalAssets": 364980000000,
    "totalPayables": 95561000000,
    "accountPayables": 68960000000,
    "otherPayables": 26601000000,
    "accruedExpenses": 0,
    "shortTermDebt": 20879000000,
    "capitalLeaseObligationsCurrent": 1632000000,
    "taxPayables": 26601000000,
    "deferredRevenue": 8249000000,
    "otherCurrentLiabilities": 50071000000,
    "totalCurrentLiabilities": 176392000000,
    "longTermDebt": 85750000000,
    "deferredRevenueNonCurrent": 10798000000,
    "deferredTaxLiabilitiesNonCurrent": 0,
    "otherNonCurrentLiabilities": 35090000000,
    "totalNonCurrentLiabilities": 131638000000,
    "otherLiabilities": 0,
    "capitalLeaseObligations": 12430000000,
    "totalLiabilities": 308030000000,
    "treasuryStock": 0,
    "preferredStock": 0,
    "commonStock": 83276000000,
    "retainedEarnings": -19154000000,
    "additionalPaidInCapital": 0,
    "accumulatedOtherComprehensiveIncomeLoss": -7172000000,
    "otherTotalStockholdersEquity": 0,
    "totalStockholdersEquity": 56950000000,
    "totalEquity": 56950000000,
    "minorityInterest": 0,
    "totalLiabilitiesAndTotalEquity": 364980000000,
    "totalInvestments": 126707000000,
    "totalDebt": 106629000000,
    "netDebt": 76686000000
  }
]
```

---

### Cash Flow Statement

Gain insights into a company's cash flow activities with the Cash Flow Statements API. Analyze cash generated and used from operations, investments, and financing activities to evaluate the financial health and sustainability of a business.

The Cash Flow Statements API provides a detailed view of a company's cash flow, giving investors and analysts essential data to understand how a company generates and spends its cash. This API is critical for: Assessing Financial Health: Evaluate a company&rsquo;s ability to generate cash from its core operations and its reliance on investments and financing. Understanding Cash Management: Track cash inflows and outflows from operating, investing, and financing activities to understand how well a company manages its cash resources. Free Cash Flow Analysis: Analyze free cash flow to determine how much cash a company has left over after paying for capital expenditures, providing a clearer picture of financial flexibility. This API delivers real-time and historical cash flow data, offering a comprehensive look at how a company manages its cash, which is essential for investment decisions, financial modeling, and credit analysis. Example Use Case A financial analyst uses the Cash Flow Statements API to evaluate a company's operating cash flow and free cash flow, helping to assess whether the company can sustain operations, invest in growth, and return value to shareholders.

**Endpoint:** `https://financialmodelingprep.com/stable/cash-flow-statement?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |
| period | string | Q1,Q2,Q3,Q4,FY,annual,quarter |

**Example Response**

```json
[
  {
    "date": "2024-09-28",
    "symbol": "AAPL",
    "reportedCurrency": "USD",
    "cik": "0000320193",
    "filingDate": "2024-11-01",
    "acceptedDate": "2024-11-01 06:01:36",
    "fiscalYear": "2024",
    "period": "FY",
    "netIncome": 93736000000,
    "depreciationAndAmortization": 11445000000,
    "deferredIncomeTax": 0,
    "stockBasedCompensation": 11688000000,
    "changeInWorkingCapital": 3651000000,
    "accountsReceivables": -5144000000,
    "inventory": -1046000000,
    "accountsPayables": 6020000000,
    "otherWorkingCapital": 3821000000,
    "otherNonCashItems": -2266000000,
    "netCashProvidedByOperatingActivities": 118254000000,
    "investmentsInPropertyPlantAndEquipment": -9447000000,
    "acquisitionsNet": 0,
    "purchasesOfInvestments": -48656000000,
    "salesMaturitiesOfInvestments": 62346000000,
    "otherInvestingActivities": -1308000000,
    "netCashProvidedByInvestingActivities": 2935000000,
    "netDebtIssuance": -5998000000,
    "longTermNetDebtIssuance": -9958000000,
    "shortTermNetDebtIssuance": 3960000000,
    "netStockIssuance": -94949000000,
    "netCommonStockIssuance": -94949000000,
    "commonStockIssuance": 0,
    "commonStockRepurchased": -94949000000,
    "netPreferredStockIssuance": 0,
    "netDividendsPaid": -15234000000,
    "commonDividendsPaid": -15234000000,
    "preferredDividendsPaid": 0,
    "otherFinancingActivities": -5802000000,
    "netCashProvidedByFinancingActivities": -121983000000,
    "effectOfForexChangesOnCash": 0,
    "netChangeInCash": -794000000,
    "cashAtEndOfPeriod": 29943000000,
    "cashAtBeginningOfPeriod": 30737000000,
    "operatingCashFlow": 118254000000,
    "capitalExpenditure": -9447000000,
    "freeCashFlow": 108807000000,
    "incomeTaxesPaid": 26102000000,
    "interestPaid": 0
  }
]
```

---

### Latest Financial Statements

**Endpoint:** `https://financialmodelingprep.com/stable/latest-financial-statements?page=0&limit=250`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| page | number | 0 |
| limit | number | 250 |

**Example Response**

```json
[
  {
    "symbol": "FGFI",
    "calendarYear": 2024,
    "period": "Q4",
    "date": "2024-12-31",
    "dateAdded": "2025-03-13 17:03:59"
  }
]
```

---

## Financial StatementsTTM

### Income Statements TTM

**Endpoint:** `https://financialmodelingprep.com/stable/income-statement-ttm?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |

**Example Response**

```json
[
  {
    "date": "2024-12-28",
    "symbol": "AAPL",
    "reportedCurrency": "USD",
    "cik": "0000320193",
    "filingDate": "2025-01-31",
    "acceptedDate": "2025-01-31 06:01:27",
    "fiscalYear": "2025",
    "period": "Q1",
    "revenue": 395760000000,
    "costOfRevenue": 211657000000,
    "grossProfit": 184103000000,
    "researchAndDevelopmentExpenses": 31942000000,
    "generalAndAdministrativeExpenses": 0,
    "sellingAndMarketingExpenses": 0,
    "sellingGeneralAndAdministrativeExpenses": 26486000000,
    "otherExpenses": 0,
    "operatingExpenses": 58428000000,
    "costAndExpenses": 270085000000,
    "netInterestIncome": 0,
    "interestIncome": 0,
    "interestExpense": 0,
    "depreciationAndAmortization": 11677000000,
    "ebitda": 137352000000,
    "ebit": 125675000000,
    "nonOperatingIncomeExcludingInterest": 0,
    "operatingIncome": 125675000000,
    "totalOtherIncomeExpensesNet": 71000000,
    "incomeBeforeTax": 125746000000,
    "incomeTaxExpense": 29596000000,
    "netIncomeFromContinuingOperations": 96150000000,
    "netIncomeFromDiscontinuedOperations": 0,
    "otherAdjustmentsToNetIncome": 0,
    "netIncome": 96150000000,
    "netIncomeDeductions": 0,
    "bottomLineNetIncome": 96150000000,
    "eps": 6.31,
    "epsDiluted": 6.3,
    "weightedAverageShsOut": 15081724000,
    "weightedAverageShsOutDil": 15150865000
  }
]
```

---

### Balance Sheet Statements TTM

**Endpoint:** `https://financialmodelingprep.com/stable/balance-sheet-statement-ttm?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |

**Example Response**

```json
[
  {
    "date": "2024-12-28",
    "symbol": "AAPL",
    "reportedCurrency": "USD",
    "cik": "0000320193",
    "filingDate": "2025-01-31",
    "acceptedDate": "2025-01-31 06:01:27",
    "fiscalYear": "2025",
    "period": "Q1",
    "cashAndCashEquivalents": 30299000000,
    "shortTermInvestments": 23476000000,
    "cashAndShortTermInvestments": 53775000000,
    "netReceivables": 59306000000,
    "accountsReceivables": 29639000000,
    "otherReceivables": 29667000000,
    "inventory": 6911000000,
    "prepaids": 0,
    "otherCurrentAssets": 13248000000,
    "totalCurrentAssets": 133240000000,
    "propertyPlantEquipmentNet": 46069000000,
    "goodwill": 0,
    "intangibleAssets": 0,
    "goodwillAndIntangibleAssets": 0,
    "longTermInvestments": 87593000000,
    "taxAssets": 0,
    "otherNonCurrentAssets": 77183000000,
    "totalNonCurrentAssets": 210845000000,
    "otherAssets": 0,
    "totalAssets": 344085000000,
    "totalPayables": 61910000000,
    "accountPayables": 61910000000,
    "otherPayables": 0,
    "accruedExpenses": 0,
    "shortTermDebt": 12843000000,
    "capitalLeaseObligationsCurrent": 0,
    "taxPayables": 0,
    "deferredRevenue": 8461000000,
    "otherCurrentLiabilities": 61151000000,
    "totalCurrentLiabilities": 144365000000,
    "longTermDebt": 83956000000,
    "deferredRevenueNonCurrent": 0,
    "deferredTaxLiabilitiesNonCurrent": 0,
    "otherNonCurrentLiabilities": 49006000000,
    "totalNonCurrentLiabilities": 132962000000,
    "otherLiabilities": 0,
    "capitalLeaseObligations": 0,
    "totalLiabilities": 277327000000,
    "treasuryStock": 0,
    "preferredStock": 0,
    "commonStock": 84768000000,
    "retainedEarnings": -11221000000,
    "additionalPaidInCapital": 0,
    "accumulatedOtherComprehensiveIncomeLoss": -6789000000,
    "otherTotalStockholdersEquity": 0,
    "totalStockholdersEquity": 66758000000,
    "totalEquity": 66758000000,
    "minorityInterest": 0,
    "totalLiabilitiesAndTotalEquity": 344085000000,
    "totalInvestments": 111069000000,
    "totalDebt": 96799000000,
    "netDebt": 66500000000
  }
]
```

---

### Cashflow Statements TTM

**Endpoint:** `https://financialmodelingprep.com/stable/cash-flow-statement-ttm?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |

**Example Response**

```json
[
  {
    "date": "2024-12-28",
    "symbol": "AAPL",
    "reportedCurrency": "USD",
    "cik": "0000320193",
    "filingDate": "2025-01-31",
    "acceptedDate": "2025-01-31 06:01:27",
    "fiscalYear": "2025",
    "period": "Q1",
    "netIncome": 96150000000,
    "depreciationAndAmortization": 11677000000,
    "deferredIncomeTax": 0,
    "stockBasedCompensation": 11977000000,
    "changeInWorkingCapital": -8224000000,
    "accountsReceivables": -9505000000,
    "inventory": -694000000,
    "accountsPayables": 3891000000,
    "otherWorkingCapital": -1916000000,
    "otherNonCashItems": -3286000000,
    "netCashProvidedByOperatingActivities": 108294000000,
    "investmentsInPropertyPlantAndEquipment": -9995000000,
    "acquisitionsNet": 0,
    "purchasesOfInvestments": -45000000000,
    "salesMaturitiesOfInvestments": 67422000000,
    "otherInvestingActivities": -1627000000,
    "netCashProvidedByInvestingActivities": 10800000000,
    "netDebtIssuance": -10967000000,
    "longTermNetDebtIssuance": -10967000000,
    "shortTermNetDebtIssuance": 0,
    "netStockIssuance": -98416000000,
    "netCommonStockIssuance": -98416000000,
    "commonStockIssuance": 0,
    "commonStockRepurchased": -98416000000,
    "netPreferredStockIssuance": 0,
    "netDividendsPaid": -15265000000,
    "commonDividendsPaid": -15265000000,
    "preferredDividendsPaid": 0,
    "otherFinancingActivities": -6121000000,
    "netCashProvidedByFinancingActivities": -130769000000,
    "effectOfForexChangesOnCash": 0,
    "netChangeInCash": -11675000000,
    "cashAtEndOfPeriod": 30299000000,
    "cashAtBeginningOfPeriod": 41974000000,
    "operatingCashFlow": 108294000000,
    "capitalExpenditure": -9995000000,
    "freeCashFlow": 98299000000,
    "incomeTaxesPaid": 37498000000,
    "interestPaid": 0
  }
]
```

---

## Ratios

### Key Metrics

Access essential financial metrics for a company with the FMP Financial Key Metrics API. Evaluate revenue, net income, P/E ratio, and more to assess performance and compare it to competitors.

The FMP Financial Key Metrics API provides crucial financial data that helps investors, analysts, and managers assess a company&rsquo;s financial performance. This endpoint offers: Revenue: Track the total income generated by the company from its operations. Net Income: Understand the company&rsquo;s profitability after all expenses and taxes have been deducted. P/E Ratio (Price-to-Earnings Ratio): Evaluate the company&rsquo;s valuation relative to its earnings, helping to determine if the stock is overvalued or undervalued. These financial key performance indicators (KPIs) are invaluable tools for business analysis, goal tracking, and competitive benchmarking. By using these metrics, you can: Assess Financial Performance: Get a clear picture of a company&rsquo;s financial health and operational efficiency. Compare to Competitors: Benchmark a company&rsquo;s performance against its competitors to identify strengths, weaknesses, and market positioning.

**Endpoint:** `https://financialmodelingprep.com/stable/key-metrics?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |
| period | string | Q1,Q2,Q3,Q4,FY,annual,quarter |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2024-09-28",
    "fiscalYear": "2024",
    "period": "FY",
    "reportedCurrency": "USD",
    "marketCap": 3495160329570,
    "enterpriseValue": 3571846329570,
    "evToSales": 9.134339201273542,
    "evToOperatingCashFlow": 30.204866893043786,
    "evToFreeCashFlow": 32.82735788662494,
    "evToEBITDA": 26.524727497716487,
    "netDebtToEBITDA": 0.5694744580836323,
    "currentRatio": 0.8673125765340832,
    "incomeQuality": 1.2615643936161134,
    "grahamNumber": 22.587017267616833,
    "grahamNetNet": -12.352478525015636,
    "taxBurden": 0.7590881483581001,
    "interestBurden": 1.0021831580314244,
    "workingCapital": -23405000000,
    "investedCapital": 22275000000,
    "returnOnAssets": 0.25682503150857583,
    "operatingReturnOnAssets": 0.3434290787011036,
    "returnOnTangibleAssets": 0.25682503150857583,
    "returnOnEquity": 1.6459350307287095,
    "returnOnInvestedCapital": 0.4430708117427921,
    "returnOnCapitalEmployed": 0.6533607652660827,
    "earningsYield": 0.026818798327209237,
    "freeCashFlowYield": 0.03113076074921754,
    "capexToOperatingCashFlow": 0.07988736110406414,
    "capexToDepreciation": 0.8254259501965924,
    "capexToRevenue": 0.02415896275269477,
    "salesGeneralAndAdministrativeToRevenue": 0,
    "researchAndDevelopementToRevenue": 0.08022299794136074,
    "stockBasedCompensationToRevenue": 0.02988990755303234,
    "intangiblesToTotalAssets": 0,
    "averageReceivables": 63614000000,
    "averagePayables": 65785500000,
    "averageInventory": 6808500000,
    "daysOfSalesOutstanding": 61.83255974529134,
    "daysOfPayablesOutstanding": 119.65847721913745,
    "daysOfInventoryOutstanding": 12.642570548414087,
    "operatingCycle": 74.47513029370543,
    "cashConversionCycle": -45.18334692543202,
    "freeCashFlowToEquity": 32121000000,
    "freeCashFlowToFirm": 117192805288.09166,
    "tangibleAssetValue": 56950000000,
    "netCurrentAssetValue": -155043000000
  }
]
```

---

### Financial Ratios

Analyze a company's financial performance using the Financial Ratios API. This API provides detailed profitability, liquidity, and efficiency ratios, enabling users to assess a company's operational and financial health across various metrics.

The Financial Ratios API delivers key ratios that help investors, analysts, and researchers evaluate a company's performance. These ratios include profitability indicators like gross profit margin and net profit margin, liquidity metrics such as current ratio and quick ratio, and efficiency measurements like asset turnover and inventory turnover. This API offers a comprehensive view of a company's financial health and operational efficiency. Profitability Ratios: Gain insight into a company's ability to generate profit, with metrics like net profit margin and return on equity. Liquidity Ratios: Understand how well a company can meet its short-term obligations using ratios like current ratio and quick ratio. Efficiency Ratios: Assess how effectively a company utilizes its assets with metrics such as asset turnover and inventory turnover. Debt Ratios: Evaluate a company's leverage and debt management through ratios like debt-to-equity and interest coverage ratios. This API is an essential tool for investors and analysts looking to analyze financial ratios and make informed decisions based on a company's financial performance. Example Use Case A portfolio manager can use the Financial Ratios API to compare liquidity ratios between companies in the same industry, helping them identify firms with stronger financial stability and more efficient operations.

**Endpoint:** `https://financialmodelingprep.com/stable/ratios?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |
| period | string | Q1,Q2,Q3,Q4,FY,annual,quarter |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2024-09-28",
    "fiscalYear": "2024",
    "period": "FY",
    "reportedCurrency": "USD",
    "grossProfitMargin": 0.4620634981523393,
    "ebitMargin": 0.31510222870075566,
    "ebitdaMargin": 0.3443707085043538,
    "operatingProfitMargin": 0.31510222870075566,
    "pretaxProfitMargin": 0.3157901466620635,
    "continuousOperationsProfitMargin": 0.23971255769943867,
    "netProfitMargin": 0.23971255769943867,
    "bottomLineProfitMargin": 0.23971255769943867,
    "receivablesTurnover": 5.903038811648023,
    "payablesTurnover": 3.0503480278422272,
    "inventoryTurnover": 28.870710952511665,
    "fixedAssetTurnover": 8.560310858143607,
    "assetTurnover": 1.0713874732862074,
    "currentRatio": 0.8673125765340832,
    "quickRatio": 0.8260068483831466,
    "solvencyRatio": 0.3414634938155374,
    "cashRatio": 0.16975259648963673,
    "priceToEarningsRatio": 37.287278415656736,
    "priceToEarningsGrowthRatio": -45.93792700808932,
    "forwardPriceToEarningsGrowthRatio": -45.93792700808932,
    "priceToBookRatio": 61.37243774486391,
    "priceToSalesRatio": 8.93822887866815,
    "priceToFreeCashFlowRatio": 32.12256867269569,
    "priceToOperatingCashFlowRatio": 29.55638142954995,
    "debtToAssetsRatio": 0.29215025480848267,
    "debtToEquityRatio": 1.872326602282704,
    "debtToCapitalRatio": 0.6518501763673821,
    "longTermDebtToCapitalRatio": 0.6009110021023125,
    "financialLeverageRatio": 6.408779631255487,
    "workingCapitalTurnoverRatio": -31.099932397502684,
    "operatingCashFlowRatio": 0.6704045534944896,
    "operatingCashFlowSalesRatio": 0.3024128274962599,
    "freeCashFlowOperatingCashFlowRatio": 0.9201126388959359,
    "debtServiceCoverageRatio": 5.024761722304708,
    "interestCoverageRatio": 0,
    "shortTermOperatingCashFlowCoverageRatio": 5.663777000814215,
    "operatingCashFlowCoverageRatio": 1.109022873702276,
    "capitalExpenditureCoverageRatio": 12.517624642743728,
    "dividendPaidAndCapexCoverageRatio": 4.7912969490701345,
    "dividendPayoutRatio": 0.16252026969360758,
    "dividendYield": 0.0043585983369965175,
    "dividendYieldPercentage": 0.43585983369965176,
    "revenuePerShare": 25.484914639368924,
    "netIncomePerShare": 6.109054070954992,
    "interestDebtPerShare": 6.949329249507765,
    "cashPerShare": 4.247388013764271,
    "bookValuePerShare": 3.711600978715614,
    "tangibleBookValuePerShare": 3.711600978715614,
    "shareholdersEquityPerShare": 3.711600978715614,
    "operatingCashFlowPerShare": 7.706965094592383,
    "capexPerShare": 0.6156891035281195,
    "freeCashFlowPerShare": 7.091275991064264,
    "netIncomePerEBT": 0.7590881483581001,
    "ebtPerEbit": 1.0021831580314244,
    "priceToFairValue": 61.37243774486391,
    "debtToMarketCap": 0.03050761336980449,
    "effectiveTaxRate": 0.24091185164189982,
    "enterpriseValueMultiple": 26.524727497716487
  }
]
```

---

### Key Metrics TTM

Retrieve a comprehensive set of trailing twelve-month (TTM) key performance metrics with the TTM Key Metrics API. Access data related to a company's profitability, capital efficiency, and liquidity, allowing for detailed analysis of its financial health over the past year.

The TTM Key Metrics API provides valuable insights into a company's recent performance, capturing data over the trailing twelve-month period. This API is ideal for: Profitability Assessment: Understand a company's ability to generate profit, with metrics such as return on assets (ROA) and earnings yield. Liquidity and Solvency Analysis: Evaluate how efficiently a company manages its short-term obligations with ratios like the current ratio and cash conversion cycle. Capital Efficiency: Assess how well a company is using its capital with metrics like return on invested capital (ROIC) and return on equity (ROE). Operational Performance: Get insights into the operational efficiency of a company through operating cycle and days of inventory outstanding (DIO). This API helps investors, analysts, and portfolio managers track financial performance trends and assess companies' efficiency in generating returns. Example Use Case An analyst can use the TTM Key Metrics API to compare the free cash flow yield of several companies within the same industry, helping them make better-informed investment decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/key-metrics-ttm?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "marketCap": 3149833928000,
    "enterpriseValueTTM": 3216333928000,
    "evToSalesTTM": 8.126980816656559,
    "evToOperatingCashFlowTTM": 29.70001965021146,
    "evToFreeCashFlowTTM": 32.71990486169747,
    "evToEBITDATTM": 23.41672438697653,
    "netDebtToEBITDATTM": 0.48415749315627005,
    "currentRatioTTM": 0.9229383853427077,
    "incomeQualityTTM": 1.1263026521060842,
    "grahamNumberTTM": 25.198029099282905,
    "grahamNetNetTTM": -11.64435843011051,
    "taxBurdenTTM": 0.7646366484818603,
    "interestBurdenTTM": 1.0005649492739208,
    "workingCapitalTTM": -11125000000,
    "investedCapitalTTM": 34944000000,
    "returnOnAssetsTTM": 0.27943676707790227,
    "operatingReturnOnAssetsTTM": 0.35448090090471257,
    "returnOnTangibleAssetsTTM": 0.27943676707790227,
    "returnOnEquityTTM": 1.4534598087751787,
    "returnOnInvestedCapitalTTM": 0.45208108089346594,
    "returnOnCapitalEmployedTTM": 0.6292559583416784,
    "earningsYieldTTM": 0.030404739849149914,
    "freeCashFlowYieldTTM": 0.03120767705439485,
    "capexToOperatingCashFlowTTM": 0.09229504866382256,
    "capexToDepreciationTTM": 0.855956153121521,
    "capexToRevenueTTM": 0.025255205174853447,
    "salesGeneralAndAdministrativeToRevenueTTM": 0,
    "researchAndDevelopementToRevenueTTM": 0.08071053163533455,
    "stockBasedCompensationToRevenueTTM": 0.030263290883363655,
    "intangiblesToTotalAssetsTTM": 0,
    "averageReceivablesTTM": 62774500000,
    "averagePayablesTTM": 65435000000,
    "averageInventoryTTM": 7098500000,
    "daysOfSalesOutstandingTTM": 54.69650798463715,
    "daysOfPayablesOutstandingTTM": 106.76306476988712,
    "daysOfInventoryOutstandingTTM": 11.917937984569374,
    "operatingCycleTTM": 66.61444596920653,
    "cashConversionCycleTTM": -40.148618800680595,
    "freeCashFlowToEquityTTM": 31799000000,
    "freeCashFlowToFirmTTM": 85497710797.9578,
    "tangibleAssetValueTTM": 66758000000,
    "netCurrentAssetValueTTM": -144087000000
  }
]
```

---

### Financial Ratios TTM

Gain access to trailing twelve-month (TTM) financial ratios with the TTM Ratios API. This API provides key performance metrics over the past year, including profitability, liquidity, and efficiency ratios.

The TTM Ratios API offers a comprehensive view of a company's financial performance, making it an essential tool for investors, analysts, and decision-makers. This API is ideal for: Profitability Analysis: Understand how efficiently a company generates profit using metrics like gross profit margin, net profit margin, and EBITDA margin. Liquidity Assessment: Evaluate a company&rsquo;s ability to meet short-term obligations with ratios such as the current ratio and quick ratio. Efficiency Insight: Examine how well a company manages its assets and liabilities with key efficiency ratios like asset turnover and inventory turnover. Leverage Evaluation: Assess a company&rsquo;s debt levels and leverage through metrics like the debt-to-equity ratio and financial leverage ratio. This API provides insights into a company's performance across key areas, helping users make more informed decisions by analyzing trends over the past twelve months. Example Use Case An investor uses the TTM Ratios API to analyze Apple&rsquo;s liquidity and profitability ratios, helping them decide whether to invest in the company based on its trailing twelve-month financial performance.

**Endpoint:** `https://financialmodelingprep.com/stable/ratios-ttm?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "grossProfitMarginTTM": 0.46518849807964424,
    "ebitMarginTTM": 0.3175535678188801,
    "ebitdaMarginTTM": 0.34705882352941175,
    "operatingProfitMarginTTM": 0.3175535678188801,
    "pretaxProfitMarginTTM": 0.31773296947645036,
    "continuousOperationsProfitMarginTTM": 0.24295027289266222,
    "netProfitMarginTTM": 0.24295027289266222,
    "bottomLineProfitMarginTTM": 0.24295027289266222,
    "receivablesTurnoverTTM": 6.673186524129093,
    "payablesTurnoverTTM": 3.4187853335486995,
    "inventoryTurnoverTTM": 30.626103313558097,
    "fixedAssetTurnoverTTM": 8.590592372311098,
    "assetTurnoverTTM": 1.1501809145995903,
    "currentRatioTTM": 0.9229383853427077,
    "quickRatioTTM": 0.8750666712845911,
    "solvencyRatioTTM": 0.3888081578786054,
    "cashRatioTTM": 0.20987774044955496,
    "priceToEarningsRatioTTM": 32.889608822880916,
    "priceToEarningsGrowthRatioTTM": 9.104441715061135,
    "forwardPriceToEarningsGrowthRatioTTM": 9.104441715061135,
    "priceToBookRatioTTM": 47.370141231313106,
    "priceToSalesRatioTTM": 7.958949686678795,
    "priceToFreeCashFlowRatioTTM": 32.04339747098139,
    "priceToOperatingCashFlowRatioTTM": 29.201395167968677,
    "debtToAssetsRatioTTM": 0.28132292892744526,
    "debtToEquityRatioTTM": 1.4499985020521886,
    "debtToCapitalRatioTTM": 0.5918364851397372,
    "longTermDebtToCapitalRatioTTM": 0.557055084464615,
    "financialLeverageRatioTTM": 5.154213727193745,
    "workingCapitalTurnoverRatioTTM": -22.92267593397046,
    "operatingCashFlowRatioTTM": 0.7501402694558931,
    "operatingCashFlowSalesRatioTTM": 0.2736355366889024,
    "freeCashFlowOperatingCashFlowRatioTTM": 0.9077049513361775,
    "debtServiceCoverageRatioTTM": 8.390251498870981,
    "interestCoverageRatioTTM": 0,
    "shortTermOperatingCashFlowCoverageRatioTTM": 8.432142022891847,
    "operatingCashFlowCoverageRatioTTM": 1.1187512267688715,
    "capitalExpenditureCoverageRatioTTM": 10.834817408704351,
    "dividendPaidAndCapexCoverageRatioTTM": 4.287173396674584,
    "dividendPayoutRatioTTM": 0.15876235049401977,
    "dividendYieldTTM": 0.0047691720717283476,
    "enterpriseValueTTM": 3216333928000,
    "revenuePerShareTTM": 26.24103186081379,
    "netIncomePerShareTTM": 6.375265851569754,
    "interestDebtPerShareTTM": 6.418298067250137,
    "cashPerShareTTM": 3.565573803101025,
    "bookValuePerShareTTM": 4.426417032959892,
    "tangibleBookValuePerShareTTM": 4.426417032959892,
    "shareholdersEquityPerShareTTM": 4.426417032959892,
    "operatingCashFlowPerShareTTM": 7.180478836504368,
    "capexPerShareTTM": 0.6627226436447186,
    "freeCashFlowPerShareTTM": 6.5177561928596495,
    "netIncomePerEBTTTM": 0.7646366484818603,
    "ebtPerEbitTTM": 1.0005649492739208,
    "priceToFairValueTTM": 47.370141231313106,
    "debtToMarketCapTTM": 0.030731461471514124,
    "effectiveTaxRateTTM": 0.23536335151813975,
    "enterpriseValueMultipleTTM": 23.41672438697653
  }
]
```

---

## Analysis

### Financial Scores

Assess a company's financial strength using the Financial Health Scores API. This API provides key metrics such as the Altman Z-Score and Piotroski Score, giving users insights into a company’s overall financial health and stability.

The Financial Health Scores API offers a detailed evaluation of a company's financial stability by calculating various scores and metrics. This API is ideal for: Bankruptcy Risk Analysis: Use the Altman Z-Score to assess the likelihood of a company facing financial distress. Profitability and Efficiency Evaluation: The Piotroski Score helps determine a company&rsquo;s financial strength by measuring profitability and operational efficiency. Working Capital Management: Track changes in working capital to understand how a company manages its short-term assets and liabilities. Leverage and Capital Structure: Assess the relationship between a company&rsquo;s total liabilities and market capitalization to evaluate its financial leverage. This API is a powerful tool for investors and analysts who need to evaluate the financial strength of a company to make informed decisions. Example Use Case A financial analyst uses the Financial Health Scores API to check Apple&rsquo;s Altman Z-Score and Piotroski Score before recommending it as a stable investment to clients.

**Endpoint:** `https://financialmodelingprep.com/stable/financial-scores?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "reportedCurrency": "USD",
    "altmanZScore": 9.322985825443649,
    "piotroskiScore": 8,
    "workingCapital": -11125000000,
    "totalAssets": 344085000000,
    "retainedEarnings": -11221000000,
    "ebit": 125675000000,
    "marketCap": 3259495258000,
    "totalLiabilities": 277327000000,
    "revenue": 395760000000
  }
]
```

---

### Owner Earnings

Retrieve a company's owner earnings with the Owner Earnings API, which provides a more accurate representation of cash available to shareholders by adjusting net income. This metric is crucial for evaluating a company’s profitability from the perspective of investors.

The Owner Earnings API offers a detailed breakdown of a company&rsquo;s cash flow adjusted for key factors, such as capital expenditures and depreciation. It is designed for: Investor Evaluation: Calculate cash truly available to shareholders, giving a clearer picture of profitability beyond net income. Valuation Analysis: Use owner earnings to make informed decisions when valuing a company for long-term investments. Capex Insight: Get insights into both maintenance and growth capital expenditures (Capex) to assess how much of the company&rsquo;s income is being reinvested. Owner Earnings Per Share: Track the value available to each share, helping determine if a stock is a good investment. This API provides a robust view of a company&rsquo;s profitability and cash flow potential, especially for value investors looking for long-term returns. Example Use Case An investor uses the Owner Earnings API to evaluate Apple&rsquo;s true cash earnings before purchasing additional shares, ensuring that the company&rsquo;s income aligns with their long-term investment strategy.

**Endpoint:** `https://financialmodelingprep.com/stable/owner-earnings?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "reportedCurrency": "USD",
    "fiscalYear": "2025",
    "period": "Q1",
    "date": "2024-12-28",
    "averagePPE": 0.13969,
    "maintenanceCapex": -2279964750,
    "ownersEarnings": 27655035250,
    "growthCapex": -660035250,
    "ownersEarningsPerShare": 1.83
  }
]
```

---

### Enterprise Values

Access a company's enterprise value using the Enterprise Values API. This metric offers a comprehensive view of a company's total market value by combining both its equity (market capitalization) and debt, providing a better understanding of its worth.

The Enterprise Values API provides key financial data to help assess a company&rsquo;s value by including: Market Capitalization: The total value of all outstanding shares based on the current stock price. Debt &amp; Cash: Includes total debt and subtracts cash and cash equivalents to get a full picture of a company&rsquo;s financial standing. Comprehensive Valuation: Enterprise value includes both equity and debt, making it a preferred measure for evaluating potential buyouts, mergers, or acquisitions. This API is ideal for analysts, investors, and finance professionals who need a complete understanding of a company&rsquo;s valuation, especially when considering its overall market position. Example Use Case A financial analyst uses the Enterprise Values API to assess Apple&rsquo;s total market value, factoring in debt and subtracting cash reserves, to determine whether it&rsquo;s a good acquisition target.

**Endpoint:** `https://financialmodelingprep.com/stable/enterprise-values?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |
| period | string | Q1,Q2,Q3,Q4,FY,annual,quarter |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2024-09-28",
    "stockPrice": 227.79,
    "numberOfShares": 15343783000,
    "marketCapitalization": 3495160329570,
    "minusCashAndCashEquivalents": 29943000000,
    "addTotalDebt": 106629000000,
    "enterpriseValue": 3571846329570
  }
]
```

---

## Growth

### Income Statement Growth

Track key financial growth metrics with the Income Statement Growth API. Analyze how revenue, profits, and expenses have evolved over time, offering insights into a company’s financial health and operational efficiency.

The Income Statement Growth API provides critical growth data, allowing users to track year-over-year changes in key income statement items, such as: Revenue Growth: Monitor changes in a company&rsquo;s total revenue, helping gauge overall business performance. Profit Growth: Assess fluctuations in gross profit, operating income, and net income, offering insights into profitability trends. Expense Growth: Analyze growth in operating expenses, cost of revenue, and specific line items like research and development or interest expenses. This API is a valuable tool for investors, analysts, and financial professionals who want to track a company's financial trends over time. Example Use Case A financial analyst can use the Income Statement Growth API to evaluate Apple&rsquo;s revenue and net income trends over the past few years, identifying whether the company is experiencing consistent growth or declines in profitability.

**Endpoint:** `https://financialmodelingprep.com/stable/income-statement-growth?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |
| period | string | Q1,Q2,Q3,Q4,FY,annual,quarter |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2024-09-28",
    "fiscalYear": "2024",
    "period": "FY",
    "reportedCurrency": "USD",
    "growthRevenue": 0.020219940775141214,
    "growthCostOfRevenue": -0.017675600199872046,
    "growthGrossProfit": 0.06819471705252206,
    "growthGrossProfitRatio": 0.04776303446712012,
    "growthResearchAndDevelopmentExpenses": 0.04863780712017383,
    "growthGeneralAndAdministrativeExpenses": 0,
    "growthSellingAndMarketingExpenses": 0,
    "growthOtherExpenses": -1,
    "growthOperatingExpenses": 0.04776924900176856,
    "growthCostAndExpenses": -0.004331112631234571,
    "growthInterestIncome": -1,
    "growthInterestExpense": -1,
    "growthDepreciationAndAmortization": -0.006424168764649709,
    "growthEBITDA": 0.07026704816404387,
    "growthOperatingIncome": 0.07799581805933456,
    "growthIncomeBeforeTax": 0.08571604417246959,
    "growthIncomeTaxExpense": 0.7770145152619318,
    "growthNetIncome": -0.033599670086086914,
    "growthEPS": -0.008116883116883088,
    "growthEPSDiluted": -0.008156606851549727,
    "growthWeightedAverageShsOut": -0.02543458616683152,
    "growthWeightedAverageShsOutDil": -0.02557791606880283,
    "growthEBIT": 0.0471407082579099,
    "growthNonOperatingIncomeExcludingInterest": 1,
    "growthNetInterestIncome": 1,
    "growthTotalOtherIncomeExpensesNet": 1.4761061946902654,
    "growthNetIncomeFromContinuingOperations": -0.033599670086086914,
    "growthOtherAdjustmentsToNetIncome": 0,
    "growthNetIncomeDeductions": 0
  }
]
```

---

### Balance Sheet Statement Growth

Analyze the growth of key balance sheet items over time with the Balance Sheet Statement Growth API. Track changes in assets, liabilities, and equity to understand the financial evolution of a company.

The Balance Sheet Statement Growth API provides year-over-year growth metrics for key balance sheet components. This API is ideal for: Asset Growth Analysis: Track changes in assets, such as cash, inventory, and long-term investments, to assess how a company&rsquo;s resources are expanding or contracting. Liability Growth Monitoring: Understand how short-term and long-term liabilities are evolving, including payables and debt. Equity Growth Tracking: Monitor shifts in shareholder equity, retained earnings, and total equity, offering insights into a company&rsquo;s financial health. This API helps financial analysts and investors evaluate a company's stability and growth by examining the evolution of its balance sheet items. Example Use Case An investor can use the Balance Sheet Statement Growth API to analyze how Apple&rsquo;s cash reserves and debt levels have changed over the past year, helping them assess the company&rsquo;s liquidity and financial health.

**Endpoint:** `https://financialmodelingprep.com/stable/balance-sheet-statement-growth?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |
| period | string | Q1,Q2,Q3,Q4,FY,annual,quarter |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2024-09-28",
    "fiscalYear": "2024",
    "period": "FY",
    "reportedCurrency": "USD",
    "growthCashAndCashEquivalents": -0.0007341898882029034,
    "growthShortTermInvestments": 0.11516302627413738,
    "growthCashAndShortTermInvestments": 0.058744212492892536,
    "growthNetReceivables": 0.08621792243994425,
    "growthInventory": 0.15084504817564365,
    "growthOtherCurrentAssets": -0.02776454576386526,
    "growthTotalCurrentAssets": 0.06562138667929733,
    "growthPropertyPlantEquipmentNet": -0.15992349565984992,
    "growthGoodwill": 0,
    "growthIntangibleAssets": 0,
    "growthGoodwillAndIntangibleAssets": 0,
    "growthLongTermInvestments": -0.09015953214513049,
    "growthTaxAssets": 0.09225857046829487,
    "growthOtherNonCurrentAssets": 0.5266933370120016,
    "growthTotalNonCurrentAssets": 0.014238076328719674,
    "growthOtherAssets": 0,
    "growthTotalAssets": 0.035160515396374756,
    "growthAccountPayables": 0.1014039066617687,
    "growthShortTermDebt": 0.32087050041121024,
    "growthTaxPayables": 2.01632838190271,
    "growthDeferredRevenue": 0.023322168465450935,
    "growthOtherCurrentLiabilities": -0.1254584832500786,
    "growthTotalCurrentLiabilities": 0.21391802240757563,
    "growthLongTermDebt": -0.10003043628845205,
    "growthDeferredRevenueNonCurrent": 0,
    "growthDeferredTaxLiabilitiesNonCurrent": 0,
    "growthOtherNonCurrentLiabilities": -0.09048495373370312,
    "growthTotalNonCurrentLiabilities": -0.09295867814151548,
    "growthOtherLiabilities": 0,
    "growthTotalLiabilities": 0.060574238130816666,
    "growthPreferredStock": 0,
    "growthCommonStock": 0.12821763398905328,
    "growthRetainedEarnings": -88.50467289719626,
    "growthAccumulatedOtherComprehensiveIncomeLoss": 0.3737338456164862,
    "growthOthertotalStockholdersEquity": 0,
    "growthTotalStockholdersEquity": -0.0836095645737457,
    "growthMinorityInterest": 0,
    "growthTotalEquity": -0.0836095645737457,
    "growthTotalLiabilitiesAndStockholdersEquity": 0.035160515396374756,
    "growthTotalInvestments": -0.04107194211936368,
    "growthTotalDebt": -0.0401393489845888,
    "growthNetDebt": -0.05469472282829777,
    "growthAccountsReceivables": 0.13223532601328453,
    "growthOtherReceivables": 0.04307907360930203,
    "growthPrepaids": 0,
    "growthTotalPayables": 0.5262653527335452,
    "growthOtherPayables": 0,
    "growthAccruedExpenses": 0,
    "growthCapitalLeaseObligationsCurrent": 0.03619047619047619,
    "growthAdditionalPaidInCapital": 0,
    "growthTreasuryStock": 0
  }
]
```

---

### Cashflow Statement Growth

Measure the growth rate of a company’s cash flow with the FMP Cashflow Statement Growth API. Determine how quickly a company’s cash flow is increasing or decreasing over time.

The FMP Cashflow Statement Growth API provides key insights into the cash flow growth rate of a company, an essential metric for assessing a company's financial health. This API is crucial for: Financial Performance Evaluation: Analyze the rate at which a company&rsquo;s cash flow is growing. A positive growth rate indicates that the company is generating more cash than it is using, which can signal strong financial health and operational efficiency. Investment Decision-Making: Use cash flow growth data to identify companies with strong cash flow generation capabilities. Companies with consistent positive cash flow growth are often more stable and may represent good investment opportunities. Risk Assessment: A negative cash flow growth rate can be a red flag, indicating that a company is using more cash than it is generating. This information can be used to evaluate the risk associated with investing in or continuing to hold a company&rsquo;s stock. Example Investor Analysis: An investor might use the Cashflow Growth API to assess a manufacturing company&rsquo;s financial health by examining its cash flow growth over the past five years. If the company shows consistent positive growth, the investor may decide to increase their investment in the company.

**Endpoint:** `https://financialmodelingprep.com/stable/cash-flow-statement-growth?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |
| period | string | Q1,Q2,Q3,Q4,FY,annual,quarter |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2024-09-28",
    "fiscalYear": "2024",
    "period": "FY",
    "reportedCurrency": "USD",
    "growthNetIncome": -0.033599670086086914,
    "growthDepreciationAndAmortization": -0.006424168764649709,
    "growthDeferredIncomeTax": 0,
    "growthStockBasedCompensation": 0.07892550540016616,
    "growthChangeInWorkingCapital": 1.555116314429071,
    "growthAccountsReceivables": -2.0473933649289098,
    "growthInventory": 0.3535228677379481,
    "growthAccountsPayables": 4.1868713605082055,
    "growthOtherWorkingCapital": 2.4402563136072373,
    "growthOtherNonCashItems": -0.017512348450830714,
    "growthNetCashProvidedByOperatingActivites": 0.06975566069312394,
    "growthInvestmentsInPropertyPlantAndEquipment": 0.13796879277306323,
    "growthAcquisitionsNet": 0,
    "growthPurchasesOfInvestments": -0.6486294175448107,
    "growthSalesMaturitiesOfInvestments": 0.3698202750801951,
    "growthOtherInvestingActivites": 0.02169035153328347,
    "growthNetCashUsedForInvestingActivites": -0.2078272604588394,
    "growthDebtRepayment": -0.012662502110417018,
    "growthCommonStockIssued": 0,
    "growthCommonStockRepurchased": -0.2243584784010316,
    "growthDividendsPaid": -0.013910149750415973,
    "growthOtherFinancingActivites": 0.03493013972055888,
    "growthNetCashUsedProvidedByFinancingActivities": -0.12439163778482412,
    "growthEffectOfForexChangesOnCash": 0,
    "growthNetChangeInCash": -1.1378472222222222,
    "growthCashAtEndOfPeriod": -0.02583205908188828,
    "growthCashAtBeginningOfPeriod": 0.23061216319013492,
    "growthOperatingCashFlow": 0.06975566069312394,
    "growthCapitalExpenditure": 0.13796879277306323,
    "growthFreeCashFlow": 0.092615279562982,
    "growthNetDebtIssuance": 0.3942026057973942,
    "growthLongTermNetDebtIssuance": -0.6812426135404356,
    "growthShortTermNetDebtIssuance": 1.995475113122172,
    "growthNetStockIssuance": -0.2243584784010316,
    "growthPreferredDividendsPaid": -0.013910149750415973,
    "growthIncomeTaxesPaid": 0.3973981476524439,
    "growthInterestPaid": -1
  }
]
```

---

### Financial Statement Growth

Analyze the growth of key financial statement items across income, balance sheet, and cash flow statements with the Financial Statement Growth API. Track changes over time to understand trends in financial performance.

The Financial Statement Growth API provides an overview of year-over-year growth in key financial metrics from income statements, balance sheets, and cash flow statements. It&rsquo;s designed for analysts and investors who want to: Assess Revenue Trends: See how a company's revenue has grown or contracted over time, highlighting overall business health. Evaluate Profitability Growth: Track growth in net income, operating income, and EBIT to gauge profitability. Monitor Asset &amp; Debt Changes: Understand the growth or reduction in assets and liabilities, providing insights into financial management. Examine Cash Flow Changes: View growth in operating cash flow and free cash flow to analyze liquidity and capital efficiency. This API helps in identifying long-term trends across financial statements, providing a comprehensive picture of a company's financial growth. Example Use Case An investor can use the Financial Statement Growth API to analyze Apple&rsquo;s revenue, net income, and free cash flow growth over the past few years, helping them assess the company&rsquo;s performance trends.

**Endpoint:** `https://financialmodelingprep.com/stable/financial-growth?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |
| period | string | Q1,Q2,Q3,Q4,FY,annual,quarter |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2024-09-28",
    "fiscalYear": "2024",
    "period": "FY",
    "reportedCurrency": "USD",
    "revenueGrowth": 0.020219940775141214,
    "grossProfitGrowth": 0.06819471705252206,
    "ebitgrowth": 0.07799581805933456,
    "operatingIncomeGrowth": 0.07799581805933456,
    "netIncomeGrowth": -0.033599670086086914,
    "epsgrowth": -0.008116883116883088,
    "epsdilutedGrowth": -0.008156606851549727,
    "weightedAverageSharesGrowth": -0.02543458616683152,
    "weightedAverageSharesDilutedGrowth": -0.02557791606880283,
    "dividendsPerShareGrowth": 0.040371570095532654,
    "operatingCashFlowGrowth": 0.06975566069312394,
    "receivablesGrowth": 0.08621792243994425,
    "inventoryGrowth": 0.15084504817564365,
    "assetGrowth": 0.035160515396374756,
    "bookValueperShareGrowth": -0.059693251557224776,
    "debtGrowth": -0.0401393489845888,
    "rdexpenseGrowth": 0.04863780712017383,
    "sgaexpensesGrowth": 0.04672709770575967,
    "freeCashFlowGrowth": 0.092615279562982,
    "tenYRevenueGrowthPerShare": 2.3937532854122625,
    "fiveYRevenueGrowthPerShare": 0.8093292228858464,
    "threeYRevenueGrowthPerShare": 0.163506592883552,
    "tenYOperatingCFGrowthPerShare": 2.1417809176982403,
    "fiveYOperatingCFGrowthPerShare": 1.051533221923415,
    "threeYOperatingCFGrowthPerShare": 0.23720294833900227,
    "tenYNetIncomeGrowthPerShare": 2.76381558093543,
    "fiveYNetIncomeGrowthPerShare": 1.0421744314966246,
    "threeYNetIncomeGrowthPerShare": 0.07761907162786884,
    "tenYShareholdersEquityGrowthPerShare": -0.19003774225234785,
    "fiveYShareholdersEquityGrowthPerShare": -0.24235004889283715,
    "threeYShareholdersEquityGrowthPerShare": -0.017459858915902907,
    "tenYDividendperShareGrowthPerShare": 1.1722201809466772,
    "fiveYDividendperShareGrowthPerShare": 0.29890046876764864,
    "threeYDividendperShareGrowthPerShare": 0.14617932692103452,
    "ebitdaGrowth": null,
    "growthCapitalExpenditure": null,
    "tenYBottomLineNetIncomeGrowthPerShare": null,
    "fiveYBottomLineNetIncomeGrowthPerShare": null,
    "threeYBottomLineNetIncomeGrowthPerShare": null
  }
]
```

---

## Formats

### Financial Reports Dates

**Endpoint:** `https://financialmodelingprep.com/stable/financial-reports-dates?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "fiscalYear": 2025,
    "period": "Q1",
    "linkXlsx": "https://financialmodelingprep.com/stable/financial-reports-json?symbol=AAPL&year=2025&period=Q1&apikey=YOUR_API_KEY",
    "linkJson": "https://financialmodelingprep.com/stable/financial-reports-xlsx?symbol=AAPL&year=2025&period=Q1&apikey=YOUR_API_KEY"
  }
]
```

---

### Financial Reports Form 10-K JSON

Access comprehensive annual reports with the FMP Annual Reports on Form 10-K API. Obtain detailed information about a company’s financial performance, business operations, and risk factors as reported to the SEC.

The FMP Annual Reports on Form 10-K API provides investors, analysts, and researchers with direct access to the annual reports that public companies in the United States are required to file with the Securities and Exchange Commission (SEC). This API is an invaluable resource for: In-Depth Financial Analysis: Access detailed financial statements and data included in a company's Form 10-K to evaluate its financial health and performance over the past fiscal year. Understanding Business Operations: Gain insights into a company&rsquo;s operations, including its business strategy, key markets, and operational challenges, as disclosed in the Form 10-K. Assessing Risk Factors: Review the risk factors section of the Form 10-K to understand the potential challenges and uncertainties that a company faces, helping to inform your investment decisions. The FMP Annual Reports on Form 10-K API makes it easy to retrieve and analyze these comprehensive reports, providing a complete picture of a company's financial and operational status.

**Endpoint:** `https://financialmodelingprep.com/stable/financial-reports-json?symbol=AAPL&year=2022&period=FY`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| year* | number | 2022 |
| period* | string | Q1,Q2,Q3,Q4,FY |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "period": "FY",
    "year": "2022",
    "Cover Page": [
      {
        "Cover Page - USD ($) shares in Thousands, $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Oct. 14, 2022",
          "Mar. 25, 2022"
        ]
      },
      {
        "Entity Information [Line Items]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Auditor Information": [
      {
        "Auditor Information": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Auditor Information [Abstract]": [
          " "
        ]
      }
    ],
    "CONSOLIDATED STATEMENTS OF OPER": [
      {
        "CONSOLIDATED STATEMENTS OF OPERATIONS - USD ($) shares in Thousands, $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Net sales": [
          394328,
          365817,
          274515
        ]
      }
    ],
    "CONSOLIDATED STATEMENTS OF COMP": [
      {
        "CONSOLIDATED STATEMENTS OF COMPREHENSIVE INCOME - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Statement of Comprehensive Income [Abstract]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "CONSOLIDATED BALANCE SHEETS": [
      {
        "CONSOLIDATED BALANCE SHEETS - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Current assets:": [
          " ",
          " "
        ]
      },
      {
        "Cash and cash equivalents": [
          23646,
          34940
        ]
      }
    ],
    "CONSOLIDATED BALANCE SHEETS (Pa": [
      {
        "CONSOLIDATED BALANCE SHEETS (Parenthetical) - $ / shares": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Statement of Financial Position [Abstract]": [
          " ",
          " "
        ]
      },
      {
        "Common stock, par value (in dollars per share)": [
          0.00001,
          0.00001
        ]
      }
    ],
    "CONSOLIDATED STATEMENTS OF SHAR": [
      {
        "CONSOLIDATED STATEMENTS OF SHAREHOLDERS' EQUITY - USD ($) $ in Millions": [
          "Total",
          "Common stock and additional paid-in capital",
          "Retained earnings/(Accumulated deficit)",
          "Retained earnings/(Accumulated deficit) Cumulative effect of change in accounting principle",
          "Accumulated other comprehensive income/(loss)",
          "Accumulated other comprehensive income/(loss) Cumulative effect of change in accounting principle"
        ]
      },
      {
        "Beginning balances at Sep. 28, 2019": [
          90488,
          45174,
          45898,
          -136,
          -584,
          136
        ]
      },
      {
        "Increase (Decrease) in Stockholders' Equity [Roll Forward]": [
          " ",
          " ",
          " ",
          " ",
          " ",
          " "
        ]
      }
    ],
    "CONSOLIDATED STATEMENTS OF CASH": [
      {
        "CONSOLIDATED STATEMENTS OF CASH FLOWS - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Statement of Cash Flows [Abstract]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Summary of Significant Accounti": [
      {
        "Summary of Significant Accounting Policies": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Accounting Policies [Abstract]": [
          " "
        ]
      }
    ],
    "Revenue": [
      {
        "Revenue": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Revenue from Contract with Customer [Abstract]": [
          " "
        ]
      }
    ],
    "Financial Instruments": [
      {
        "Financial Instruments": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Investments, All Other Investments [Abstract]": [
          " "
        ]
      }
    ],
    "Consolidated Financial Statemen": [
      {
        "Consolidated Financial Statement Details": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Organization, Consolidation and Presentation of Financial Statements [Abstract]": [
          " "
        ]
      }
    ],
    "Income Taxes": [
      {
        "Income Taxes": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Income Tax Disclosure [Abstract]": [
          " "
        ]
      }
    ],
    "Leases": [
      {
        "Leases": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Leases [Abstract]": [
          " "
        ]
      }
    ],
    "Debt": [
      {
        "Debt": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Debt Disclosure [Abstract]": [
          " "
        ]
      }
    ],
    "Shareholders' Equity": [
      {
        "Shareholders' Equity": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Equity [Abstract]": [
          " "
        ]
      }
    ],
    "Benefit Plans": [
      {
        "Benefit Plans": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Share-Based Payment Arrangement [Abstract]": [
          " "
        ]
      }
    ],
    "Commitments and Contingencies": [
      {
        "Commitments and Contingencies": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Commitments and Contingencies Disclosure [Abstract]": [
          " "
        ]
      }
    ],
    "Segment Information and Geograp": [
      {
        "Segment Information and Geographic Data": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Segment Reporting [Abstract]": [
          " "
        ]
      }
    ],
    "Summary of Significant Accoun_2": [
      {
        "Summary of Significant Accounting Policies (Policies)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Accounting Policies [Abstract]": [
          " "
        ]
      }
    ],
    "Summary of Significant Accoun_3": [
      {
        "Summary of Significant Accounting Policies (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Accounting Policies [Abstract]": [
          " "
        ]
      }
    ],
    "Revenue (Tables)": [
      {
        "Revenue (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Revenue from Contract with Customer [Abstract]": [
          " "
        ]
      }
    ],
    "Financial Instruments (Tables)": [
      {
        "Financial Instruments (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Investments, All Other Investments [Abstract]": [
          " "
        ]
      }
    ],
    "Consolidated Financial Statem_2": [
      {
        "Consolidated Financial Statement Details (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Organization, Consolidation and Presentation of Financial Statements [Abstract]": [
          " "
        ]
      }
    ],
    "Income Taxes (Tables)": [
      {
        "Income Taxes (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Income Tax Disclosure [Abstract]": [
          " "
        ]
      }
    ],
    "Leases (Tables)": [
      {
        "Leases (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Leases [Abstract]": [
          " "
        ]
      }
    ],
    "Debt (Tables)": [
      {
        "Debt (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Debt Disclosure [Abstract]": [
          " "
        ]
      }
    ],
    "Shareholders' Equity (Tables)": [
      {
        "Shareholders' Equity (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Equity [Abstract]": [
          " "
        ]
      }
    ],
    "Benefit Plans (Tables)": [
      {
        "Benefit Plans (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Share-Based Payment Arrangement [Abstract]": [
          " "
        ]
      }
    ],
    "Commitments and Contingencies (": [
      {
        "Commitments and Contingencies (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Commitments and Contingencies Disclosure [Abstract]": [
          " "
        ]
      }
    ],
    "Segment Information and Geogr_2": [
      {
        "Segment Information and Geographic Data (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Segment Reporting [Abstract]": [
          " "
        ]
      }
    ],
    "Summary of Significant Accoun_4": [
      {
        "Summary of Significant Accounting Policies - Additional Information (Details) $ in Billions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022 USD ($) performanceObligation",
          "Sep. 25, 2021 USD ($)",
          "Sep. 26, 2020 USD ($)"
        ]
      },
      {
        "Significant Accounting Policies [Line Items]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Summary of Significant Accoun_5": [
      {
        "Summary of Significant Accounting Policies - Computation of Basic and Diluted Earnings Per Share (Details) - USD ($) $ / shares in Units, shares in Thousands, $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Numerator:": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Revenue - Net Sales Disaggregat": [
      {
        "Revenue - Net Sales Disaggregated by Significant Products and Services (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Disaggregation of Revenue [Line Items]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Revenue - Additional Informatio": [
      {
        "Revenue - Additional Information (Details) - USD ($) $ in Billions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Revenue from Contract with Customer [Abstract]": [
          " ",
          " "
        ]
      },
      {
        "Total deferred revenue": [
          12.4,
          11.9
        ]
      }
    ],
    "Revenue - Deferred Revenue, Exp": [
      {
        "Revenue - Deferred Revenue, Expected Timing of Realization (Details)": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Revenue, Remaining Performance Obligation, Expected Timing of Satisfaction, Start Date [Axis]: 2022-09-25": [
          " "
        ]
      },
      {
        "Revenue, Remaining Performance Obligation, Expected Timing of Satisfaction [Line Items]": [
          " "
        ]
      }
    ],
    "Financial Instruments - Cash, C": [
      {
        "Financial Instruments - Cash, Cash Equivalents and Marketable Securities (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Debt Securities, Available-for-sale [Line Items]": [
          " ",
          " "
        ]
      },
      {
        "Cash, Cash Equivalents and Marketable Securities, Adjusted Cost": [
          183061,
          189961
        ]
      }
    ],
    "Financial Instruments - Non-Cur": [
      {
        "Financial Instruments - Non-Current Marketable Debt Securities by Contractual Maturity (Details) $ in Millions": [
          "Sep. 24, 2022 USD ($)"
        ]
      },
      {
        "Fair value of non-current marketable debt securities by contractual maturity": [
          " "
        ]
      },
      {
        "Due after 1 year through 5 years": [
          87031
        ]
      }
    ],
    "Financial Instruments - Additio": [
      {
        "Financial Instruments - Additional Information (Details) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022 USD ($) Customer Vendor",
          "Sep. 25, 2021 Vendor"
        ]
      },
      {
        "Financial Instruments [Line Items]": [
          " ",
          " "
        ]
      }
    ],
    "Financial Instruments - Notiona": [
      {
        "Financial Instruments - Notional Amounts Associated with Derivative Instruments (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Derivatives designated as accounting hedges | Foreign exchange contracts": [
          " ",
          " "
        ]
      },
      {
        "Derivative [Line Items]": [
          " ",
          " "
        ]
      }
    ],
    "Financial Instruments - Gross F": [
      {
        "Financial Instruments - Gross Fair Values of Derivative Assets and Liabilities (Details) - Level 2 $ in Millions": [
          "Sep. 24, 2022 USD ($)"
        ]
      },
      {
        "Other current assets and other non-current assets | Foreign exchange contracts": [
          " "
        ]
      },
      {
        "Derivative assets:": [
          " "
        ]
      }
    ],
    "Financial Instruments - Derivat": [
      {
        "Financial Instruments - Derivative Instruments Designated as Fair Value Hedges and Related Hedged Items (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Current and non-current marketable securities": [
          " ",
          " "
        ]
      },
      {
        "Derivatives, Fair Value [Line Items]": [
          " ",
          " "
        ]
      }
    ],
    "Consolidated Financial Statem_3": [
      {
        "Consolidated Financial Statement Details - Property, Plant and Equipment, Net (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Property, Plant and Equipment [Line Items]": [
          " ",
          " "
        ]
      },
      {
        "Gross property, plant and equipment": [
          114457,
          109723
        ]
      }
    ],
    "Consolidated Financial Statem_4": [
      {
        "Consolidated Financial Statement Details - Other Non-Current Liabilities (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Organization, Consolidation and Presentation of Financial Statements [Abstract]": [
          " ",
          " "
        ]
      },
      {
        "Long-term taxes payable": [
          16657,
          24689
        ]
      }
    ],
    "Consolidated Financial Statem_5": [
      {
        "Consolidated Financial Statement Details - Other Income/(Expense), Net (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Organization, Consolidation and Presentation of Financial Statements [Abstract]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Income Taxes - Provision for In": [
      {
        "Income Taxes - Provision for Income Taxes (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Federal:": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Income Taxes - Additional Infor": [
      {
        "Income Taxes - Additional Information (Details) $ in Millions, € in Billions": [
          null,
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Aug. 30, 2016 EUR (€) Subsidiary",
          "Sep. 24, 2022 USD ($)",
          "Sep. 25, 2021 USD ($)",
          "Sep. 26, 2020 USD ($)",
          "Sep. 24, 2022 EUR (€)",
          "Sep. 28, 2019 USD ($)"
        ]
      },
      {
        "Income Tax Contingency [Line Items]": [
          " ",
          " ",
          " ",
          " ",
          " ",
          " "
        ]
      }
    ],
    "Income Taxes - Reconciliation o": [
      {
        "Income Taxes - Reconciliation of Provision for Income Taxes to Amount Computed by Applying the Statutory Federal Income Tax Rate to Income Before Provision for Income Taxes (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Income Tax Disclosure [Abstract]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Income Taxes - Significant Comp": [
      {
        "Income Taxes - Significant Components of Deferred Tax Assets and Liabilities (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Deferred tax assets:": [
          " ",
          " "
        ]
      },
      {
        "Amortization and depreciation": [
          1496,
          5575
        ]
      }
    ],
    "Income Taxes - Aggregate Change": [
      {
        "Income Taxes - Aggregate Changes in Gross Unrecognized Tax Benefits (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Reconciliation of Unrecognized Tax Benefits, Excluding Amounts Pertaining to Examined Tax Returns [Roll Forward]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Leases - Additional Information": [
      {
        "Leases - Additional Information (Details) - USD ($) $ in Billions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Lessee, Lease, Description [Line Items]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Leases - ROU Assets and Lease L": [
      {
        "Leases - ROU Assets and Lease Liabilities (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Lease-Related Assets and Liabilities": [
          " ",
          " "
        ]
      },
      {
        "Operating lease right-of-use assets": [
          10417,
          10087
        ]
      }
    ],
    "Leases - Lease Liability Maturi": [
      {
        "Leases - Lease Liability Maturities (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Operating Leases": [
          " ",
          " "
        ]
      },
      {
        "2023": [
          1758,
          " "
        ]
      }
    ],
    "Debt - Additional Information (": [
      {
        "Debt - Additional Information (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Debt Instrument [Line Items]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Debt - Summary of Cash Flows As": [
      {
        "Debt - Summary of Cash Flows Associated with Commercial Paper (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Maturities 90 days or less:": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Debt - Summary of Term Debt (De": [
      {
        "Debt - Summary of Term Debt (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Debt Instrument [Line Items]": [
          " ",
          " "
        ]
      }
    ],
    "Debt - Future Principal Payment": [
      {
        "Debt - Future Principal Payments for Term Debt (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Debt Disclosure [Abstract]": [
          " ",
          " "
        ]
      },
      {
        "2023": [
          11139,
          " "
        ]
      }
    ],
    "Shareholders' Equity - Addition": [
      {
        "Shareholders' Equity - Additional Information (Details) shares in Millions, $ in Billions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022 USD ($) shares"
        ]
      },
      {
        "Stockholders' Equity Note [Abstract]": [
          " "
        ]
      }
    ],
    "Shareholders' Equity - Shares o": [
      {
        "Shareholders' Equity - Shares of Common Stock (Details) - shares shares in Thousands": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Increase (Decrease) in Shares of Common Stock Outstanding [Roll Forward]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Benefit Plans - Additional Info": [
      {
        "Benefit Plans - Additional Information (Details) shares in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022 USD ($) shares",
          "Sep. 25, 2021 USD ($) shares",
          "Sep. 26, 2020 USD ($) shares",
          "Mar. 04, 2022 shares",
          "Nov. 09, 2021 shares",
          "Mar. 10, 2015 shares"
        ]
      },
      {
        "Share-based Compensation Arrangement by Share-based Payment Award [Line Items]": [
          " ",
          " ",
          " ",
          " ",
          " ",
          " "
        ]
      }
    ],
    "Benefit Plans - Restricted Stoc": [
      {
        "Benefit Plans - Restricted Stock Units Activity and Related Information (Details) - Restricted stock units - USD ($) $ / shares in Units, shares in Thousands, $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Number of Restricted Stock Units": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Benefit Plans - Summary of Shar": [
      {
        "Benefit Plans - Summary of Share-Based Compensation Expense and the Related Income Tax Benefit (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Share-Based Payment Arrangement [Abstract]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Commitments and Contingencies -": [
      {
        "Commitments and Contingencies - Future Payments Under Unconditional Purchase Obligations (Details) $ in Millions": [
          "Sep. 24, 2022 USD ($)"
        ]
      },
      {
        "Unconditional Purchase Obligation, Fiscal Year Maturity [Abstract]": [
          " "
        ]
      },
      {
        "2023": [
          13488
        ]
      }
    ],
    "Segment Information and Geogr_3": [
      {
        "Segment Information and Geographic Data - Information by Reportable Segment (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Segment Reporting Information [Line Items]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Segment Information and Geogr_4": [
      {
        "Segment Information and Geographic Data - Reconciliation of Segment Operating Income to the Consolidated Statements of Operations (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Segment Reporting, Reconciling Item for Operating Profit (Loss) from Segment to Consolidated [Line Items]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Segment Information and Geogr_5": [
      {
        "Segment Information and Geographic Data - Net Sales (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Revenues from External Customers and Long-Lived Assets [Line Items]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Segment Information and Geogr_6": [
      {
        "Segment Information and Geographic Data - Long-Lived Assets (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Revenues from External Customers and Long-Lived Assets [Line Items]": [
          " ",
          " "
        ]
      },
      {
        "Long-lived assets": [
          42117,
          39440
        ]
      }
    ]
  }
]
```

---

### Financial Reports Form 10-K XLSX

Download detailed 10-K reports in XLSX format with the Financial Reports Form 10-K XLSX API. Effortlessly access and analyze annual financial data for companies in a spreadsheet-friendly format.

The Financial Reports Form 10-K XLSX API provides users with the ability to download 10-K financial reports in a format that can be opened in Excel. This allows for: Detailed Financial Analysis: View comprehensive financial data, including income statements, balance sheets, and cash flow statements, with Excel&rsquo;s built-in analysis tools. Flexible Data Usage: Customize and manipulate the data for further analysis, enabling users to run financial models or track trends. Efficient Reporting: Create financial summaries, pivot tables, and other visualizations based on the data from 10-K reports. Historical Data Access: Download reports from previous fiscal years for detailed historical comparisons. This API makes it simple to work with financial data in a spreadsheet, streamlining analysis and reporting workflows. Example Use Case A financial analyst can download Apple&rsquo;s 2022 10-K report in XLSX format, making it easier to import the data into their financial models and analyze trends over the fiscal year.

**Endpoint:** `https://financialmodelingprep.com/stable/financial-reports-xlsx?symbol=AAPL&year=2022&period=FY`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| year* | number | 2022 |
| period* | string | Q1,Q2,Q3,Q4,FY |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "period": "FY",
    "year": "2022",
    "Cover Page": [
      {
        "Cover Page - USD ($) shares in Thousands, $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Oct. 14, 2022",
          "Mar. 25, 2022"
        ]
      },
      {
        "Entity Information [Line Items]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Auditor Information": [
      {
        "Auditor Information": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Auditor Information [Abstract]": [
          " "
        ]
      }
    ],
    "CONSOLIDATED STATEMENTS OF OPER": [
      {
        "CONSOLIDATED STATEMENTS OF OPERATIONS - USD ($) shares in Thousands, $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Net sales": [
          394328,
          365817,
          274515
        ]
      }
    ],
    "CONSOLIDATED STATEMENTS OF COMP": [
      {
        "CONSOLIDATED STATEMENTS OF COMPREHENSIVE INCOME - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Statement of Comprehensive Income [Abstract]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "CONSOLIDATED BALANCE SHEETS": [
      {
        "CONSOLIDATED BALANCE SHEETS - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Current assets:": [
          " ",
          " "
        ]
      },
      {
        "Cash and cash equivalents": [
          23646,
          34940
        ]
      }
    ],
    "CONSOLIDATED BALANCE SHEETS (Pa": [
      {
        "CONSOLIDATED BALANCE SHEETS (Parenthetical) - $ / shares": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Statement of Financial Position [Abstract]": [
          " ",
          " "
        ]
      },
      {
        "Common stock, par value (in dollars per share)": [
          0.00001,
          0.00001
        ]
      }
    ],
    "CONSOLIDATED STATEMENTS OF SHAR": [
      {
        "CONSOLIDATED STATEMENTS OF SHAREHOLDERS' EQUITY - USD ($) $ in Millions": [
          "Total",
          "Common stock and additional paid-in capital",
          "Retained earnings/(Accumulated deficit)",
          "Retained earnings/(Accumulated deficit) Cumulative effect of change in accounting principle",
          "Accumulated other comprehensive income/(loss)",
          "Accumulated other comprehensive income/(loss) Cumulative effect of change in accounting principle"
        ]
      },
      {
        "Beginning balances at Sep. 28, 2019": [
          90488,
          45174,
          45898,
          -136,
          -584,
          136
        ]
      },
      {
        "Increase (Decrease) in Stockholders' Equity [Roll Forward]": [
          " ",
          " ",
          " ",
          " ",
          " ",
          " "
        ]
      }
    ],
    "CONSOLIDATED STATEMENTS OF CASH": [
      {
        "CONSOLIDATED STATEMENTS OF CASH FLOWS - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Statement of Cash Flows [Abstract]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Summary of Significant Accounti": [
      {
        "Summary of Significant Accounting Policies": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Accounting Policies [Abstract]": [
          " "
        ]
      }
    ],
    "Revenue": [
      {
        "Revenue": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Revenue from Contract with Customer [Abstract]": [
          " "
        ]
      }
    ],
    "Financial Instruments": [
      {
        "Financial Instruments": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Investments, All Other Investments [Abstract]": [
          " "
        ]
      }
    ],
    "Consolidated Financial Statemen": [
      {
        "Consolidated Financial Statement Details": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Organization, Consolidation and Presentation of Financial Statements [Abstract]": [
          " "
        ]
      }
    ],
    "Income Taxes": [
      {
        "Income Taxes": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Income Tax Disclosure [Abstract]": [
          " "
        ]
      }
    ],
    "Leases": [
      {
        "Leases": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Leases [Abstract]": [
          " "
        ]
      }
    ],
    "Debt": [
      {
        "Debt": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Debt Disclosure [Abstract]": [
          " "
        ]
      }
    ],
    "Shareholders' Equity": [
      {
        "Shareholders' Equity": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Equity [Abstract]": [
          " "
        ]
      }
    ],
    "Benefit Plans": [
      {
        "Benefit Plans": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Share-Based Payment Arrangement [Abstract]": [
          " "
        ]
      }
    ],
    "Commitments and Contingencies": [
      {
        "Commitments and Contingencies": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Commitments and Contingencies Disclosure [Abstract]": [
          " "
        ]
      }
    ],
    "Segment Information and Geograp": [
      {
        "Segment Information and Geographic Data": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Segment Reporting [Abstract]": [
          " "
        ]
      }
    ],
    "Summary of Significant Accoun_2": [
      {
        "Summary of Significant Accounting Policies (Policies)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Accounting Policies [Abstract]": [
          " "
        ]
      }
    ],
    "Summary of Significant Accoun_3": [
      {
        "Summary of Significant Accounting Policies (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Accounting Policies [Abstract]": [
          " "
        ]
      }
    ],
    "Revenue (Tables)": [
      {
        "Revenue (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Revenue from Contract with Customer [Abstract]": [
          " "
        ]
      }
    ],
    "Financial Instruments (Tables)": [
      {
        "Financial Instruments (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Investments, All Other Investments [Abstract]": [
          " "
        ]
      }
    ],
    "Consolidated Financial Statem_2": [
      {
        "Consolidated Financial Statement Details (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Organization, Consolidation and Presentation of Financial Statements [Abstract]": [
          " "
        ]
      }
    ],
    "Income Taxes (Tables)": [
      {
        "Income Taxes (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Income Tax Disclosure [Abstract]": [
          " "
        ]
      }
    ],
    "Leases (Tables)": [
      {
        "Leases (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Leases [Abstract]": [
          " "
        ]
      }
    ],
    "Debt (Tables)": [
      {
        "Debt (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Debt Disclosure [Abstract]": [
          " "
        ]
      }
    ],
    "Shareholders' Equity (Tables)": [
      {
        "Shareholders' Equity (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Equity [Abstract]": [
          " "
        ]
      }
    ],
    "Benefit Plans (Tables)": [
      {
        "Benefit Plans (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Share-Based Payment Arrangement [Abstract]": [
          " "
        ]
      }
    ],
    "Commitments and Contingencies (": [
      {
        "Commitments and Contingencies (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Commitments and Contingencies Disclosure [Abstract]": [
          " "
        ]
      }
    ],
    "Segment Information and Geogr_2": [
      {
        "Segment Information and Geographic Data (Tables)": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Segment Reporting [Abstract]": [
          " "
        ]
      }
    ],
    "Summary of Significant Accoun_4": [
      {
        "Summary of Significant Accounting Policies - Additional Information (Details) $ in Billions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022 USD ($) performanceObligation",
          "Sep. 25, 2021 USD ($)",
          "Sep. 26, 2020 USD ($)"
        ]
      },
      {
        "Significant Accounting Policies [Line Items]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Summary of Significant Accoun_5": [
      {
        "Summary of Significant Accounting Policies - Computation of Basic and Diluted Earnings Per Share (Details) - USD ($) $ / shares in Units, shares in Thousands, $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Numerator:": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Revenue - Net Sales Disaggregat": [
      {
        "Revenue - Net Sales Disaggregated by Significant Products and Services (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Disaggregation of Revenue [Line Items]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Revenue - Additional Informatio": [
      {
        "Revenue - Additional Information (Details) - USD ($) $ in Billions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Revenue from Contract with Customer [Abstract]": [
          " ",
          " "
        ]
      },
      {
        "Total deferred revenue": [
          12.4,
          11.9
        ]
      }
    ],
    "Revenue - Deferred Revenue, Exp": [
      {
        "Revenue - Deferred Revenue, Expected Timing of Realization (Details)": [
          "Sep. 24, 2022"
        ]
      },
      {
        "Revenue, Remaining Performance Obligation, Expected Timing of Satisfaction, Start Date [Axis]: 2022-09-25": [
          " "
        ]
      },
      {
        "Revenue, Remaining Performance Obligation, Expected Timing of Satisfaction [Line Items]": [
          " "
        ]
      }
    ],
    "Financial Instruments - Cash, C": [
      {
        "Financial Instruments - Cash, Cash Equivalents and Marketable Securities (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Debt Securities, Available-for-sale [Line Items]": [
          " ",
          " "
        ]
      },
      {
        "Cash, Cash Equivalents and Marketable Securities, Adjusted Cost": [
          183061,
          189961
        ]
      }
    ],
    "Financial Instruments - Non-Cur": [
      {
        "Financial Instruments - Non-Current Marketable Debt Securities by Contractual Maturity (Details) $ in Millions": [
          "Sep. 24, 2022 USD ($)"
        ]
      },
      {
        "Fair value of non-current marketable debt securities by contractual maturity": [
          " "
        ]
      },
      {
        "Due after 1 year through 5 years": [
          87031
        ]
      }
    ],
    "Financial Instruments - Additio": [
      {
        "Financial Instruments - Additional Information (Details) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022 USD ($) Customer Vendor",
          "Sep. 25, 2021 Vendor"
        ]
      },
      {
        "Financial Instruments [Line Items]": [
          " ",
          " "
        ]
      }
    ],
    "Financial Instruments - Notiona": [
      {
        "Financial Instruments - Notional Amounts Associated with Derivative Instruments (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Derivatives designated as accounting hedges | Foreign exchange contracts": [
          " ",
          " "
        ]
      },
      {
        "Derivative [Line Items]": [
          " ",
          " "
        ]
      }
    ],
    "Financial Instruments - Gross F": [
      {
        "Financial Instruments - Gross Fair Values of Derivative Assets and Liabilities (Details) - Level 2 $ in Millions": [
          "Sep. 24, 2022 USD ($)"
        ]
      },
      {
        "Other current assets and other non-current assets | Foreign exchange contracts": [
          " "
        ]
      },
      {
        "Derivative assets:": [
          " "
        ]
      }
    ],
    "Financial Instruments - Derivat": [
      {
        "Financial Instruments - Derivative Instruments Designated as Fair Value Hedges and Related Hedged Items (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Current and non-current marketable securities": [
          " ",
          " "
        ]
      },
      {
        "Derivatives, Fair Value [Line Items]": [
          " ",
          " "
        ]
      }
    ],
    "Consolidated Financial Statem_3": [
      {
        "Consolidated Financial Statement Details - Property, Plant and Equipment, Net (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Property, Plant and Equipment [Line Items]": [
          " ",
          " "
        ]
      },
      {
        "Gross property, plant and equipment": [
          114457,
          109723
        ]
      }
    ],
    "Consolidated Financial Statem_4": [
      {
        "Consolidated Financial Statement Details - Other Non-Current Liabilities (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Organization, Consolidation and Presentation of Financial Statements [Abstract]": [
          " ",
          " "
        ]
      },
      {
        "Long-term taxes payable": [
          16657,
          24689
        ]
      }
    ],
    "Consolidated Financial Statem_5": [
      {
        "Consolidated Financial Statement Details - Other Income/(Expense), Net (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Organization, Consolidation and Presentation of Financial Statements [Abstract]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Income Taxes - Provision for In": [
      {
        "Income Taxes - Provision for Income Taxes (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Federal:": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Income Taxes - Additional Infor": [
      {
        "Income Taxes - Additional Information (Details) $ in Millions, € in Billions": [
          null,
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Aug. 30, 2016 EUR (€) Subsidiary",
          "Sep. 24, 2022 USD ($)",
          "Sep. 25, 2021 USD ($)",
          "Sep. 26, 2020 USD ($)",
          "Sep. 24, 2022 EUR (€)",
          "Sep. 28, 2019 USD ($)"
        ]
      },
      {
        "Income Tax Contingency [Line Items]": [
          " ",
          " ",
          " ",
          " ",
          " ",
          " "
        ]
      }
    ],
    "Income Taxes - Reconciliation o": [
      {
        "Income Taxes - Reconciliation of Provision for Income Taxes to Amount Computed by Applying the Statutory Federal Income Tax Rate to Income Before Provision for Income Taxes (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Income Tax Disclosure [Abstract]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Income Taxes - Significant Comp": [
      {
        "Income Taxes - Significant Components of Deferred Tax Assets and Liabilities (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Deferred tax assets:": [
          " ",
          " "
        ]
      },
      {
        "Amortization and depreciation": [
          1496,
          5575
        ]
      }
    ],
    "Income Taxes - Aggregate Change": [
      {
        "Income Taxes - Aggregate Changes in Gross Unrecognized Tax Benefits (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Reconciliation of Unrecognized Tax Benefits, Excluding Amounts Pertaining to Examined Tax Returns [Roll Forward]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Leases - Additional Information": [
      {
        "Leases - Additional Information (Details) - USD ($) $ in Billions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Lessee, Lease, Description [Line Items]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Leases - ROU Assets and Lease L": [
      {
        "Leases - ROU Assets and Lease Liabilities (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Lease-Related Assets and Liabilities": [
          " ",
          " "
        ]
      },
      {
        "Operating lease right-of-use assets": [
          10417,
          10087
        ]
      }
    ],
    "Leases - Lease Liability Maturi": [
      {
        "Leases - Lease Liability Maturities (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Operating Leases": [
          " ",
          " "
        ]
      },
      {
        "2023": [
          1758,
          " "
        ]
      }
    ],
    "Debt - Additional Information (": [
      {
        "Debt - Additional Information (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Debt Instrument [Line Items]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Debt - Summary of Cash Flows As": [
      {
        "Debt - Summary of Cash Flows Associated with Commercial Paper (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Maturities 90 days or less:": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Debt - Summary of Term Debt (De": [
      {
        "Debt - Summary of Term Debt (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Debt Instrument [Line Items]": [
          " ",
          " "
        ]
      }
    ],
    "Debt - Future Principal Payment": [
      {
        "Debt - Future Principal Payments for Term Debt (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Debt Disclosure [Abstract]": [
          " ",
          " "
        ]
      },
      {
        "2023": [
          11139,
          " "
        ]
      }
    ],
    "Shareholders' Equity - Addition": [
      {
        "Shareholders' Equity - Additional Information (Details) shares in Millions, $ in Billions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022 USD ($) shares"
        ]
      },
      {
        "Stockholders' Equity Note [Abstract]": [
          " "
        ]
      }
    ],
    "Shareholders' Equity - Shares o": [
      {
        "Shareholders' Equity - Shares of Common Stock (Details) - shares shares in Thousands": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Increase (Decrease) in Shares of Common Stock Outstanding [Roll Forward]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Benefit Plans - Additional Info": [
      {
        "Benefit Plans - Additional Information (Details) shares in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022 USD ($) shares",
          "Sep. 25, 2021 USD ($) shares",
          "Sep. 26, 2020 USD ($) shares",
          "Mar. 04, 2022 shares",
          "Nov. 09, 2021 shares",
          "Mar. 10, 2015 shares"
        ]
      },
      {
        "Share-based Compensation Arrangement by Share-based Payment Award [Line Items]": [
          " ",
          " ",
          " ",
          " ",
          " ",
          " "
        ]
      }
    ],
    "Benefit Plans - Restricted Stoc": [
      {
        "Benefit Plans - Restricted Stock Units Activity and Related Information (Details) - Restricted stock units - USD ($) $ / shares in Units, shares in Thousands, $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Number of Restricted Stock Units": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Benefit Plans - Summary of Shar": [
      {
        "Benefit Plans - Summary of Share-Based Compensation Expense and the Related Income Tax Benefit (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Share-Based Payment Arrangement [Abstract]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Commitments and Contingencies -": [
      {
        "Commitments and Contingencies - Future Payments Under Unconditional Purchase Obligations (Details) $ in Millions": [
          "Sep. 24, 2022 USD ($)"
        ]
      },
      {
        "Unconditional Purchase Obligation, Fiscal Year Maturity [Abstract]": [
          " "
        ]
      },
      {
        "2023": [
          13488
        ]
      }
    ],
    "Segment Information and Geogr_3": [
      {
        "Segment Information and Geographic Data - Information by Reportable Segment (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Segment Reporting Information [Line Items]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Segment Information and Geogr_4": [
      {
        "Segment Information and Geographic Data - Reconciliation of Segment Operating Income to the Consolidated Statements of Operations (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Segment Reporting, Reconciling Item for Operating Profit (Loss) from Segment to Consolidated [Line Items]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Segment Information and Geogr_5": [
      {
        "Segment Information and Geographic Data - Net Sales (Details) - USD ($) $ in Millions": [
          "12 Months Ended"
        ]
      },
      {
        "items": [
          "Sep. 24, 2022",
          "Sep. 25, 2021",
          "Sep. 26, 2020"
        ]
      },
      {
        "Revenues from External Customers and Long-Lived Assets [Line Items]": [
          " ",
          " ",
          " "
        ]
      }
    ],
    "Segment Information and Geogr_6": [
      {
        "Segment Information and Geographic Data - Long-Lived Assets (Details) - USD ($) $ in Millions": [
          "Sep. 24, 2022",
          "Sep. 25, 2021"
        ]
      },
      {
        "Revenues from External Customers and Long-Lived Assets [Line Items]": [
          " ",
          " "
        ]
      },
      {
        "Long-lived assets": [
          42117,
          39440
        ]
      }
    ]
  }
]
```

---

## Segmentation

### Revenue Product Segmentation

Access detailed revenue breakdowns by product line with the Revenue Product Segmentation API. Understand which products drive a company's earnings and get insights into the performance of individual product segments.

The Revenue Product Segmentation API provides a comprehensive breakdown of a company&rsquo;s revenue by product, making it easy to analyze performance across different product categories. This API is ideal for: Product-Specific Revenue Analysis: Understand how much each product contributes to the company&rsquo;s total earnings. Strategic Insights: Gain insights into the growth or decline of specific product segments to inform investment decisions or corporate strategy. Competitive Benchmarking: Compare product segment revenues across different companies in the same industry to gauge market position. This API offers a detailed view of product-level revenue, helping users identify growth drivers and track the financial health of specific product lines. Example Use Case An investor can use the Revenue Product Segmentation API to see how much of Apple&rsquo;s earnings come from iPhone sales compared to other products, such as Macs or wearables.

**Endpoint:** `https://financialmodelingprep.com/stable/revenue-product-segmentation?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| period | string | annual,quarter |
| structure | string | flat |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "fiscalYear": 2024,
    "period": "FY",
    "reportedCurrency": null,
    "date": "2024-09-28",
    "data": {
      "Mac": 29984000000,
      "Service": 96169000000,
      "Wearables, Home and Accessories": 37005000000,
      "iPad": 26694000000,
      "iPhone": 201183000000
    }
  }
]
```

---

### Revenue Geographic Segments

Access detailed revenue breakdowns by geographic region with the Revenue Geographic Segments API. Analyze how different regions contribute to a company’s total revenue and identify key markets for growth.

The Revenue Geographic Segments API allows users to retrieve revenue data segmented by geographical regions, helping investors and analysts understand the performance of a company in different markets. This API is ideal for: Regional Revenue Analysis: Break down revenue contributions by geographical area to see which regions are driving growth. Market Performance Insights: Analyze how a company is performing in key regions like the Americas, Europe, and Greater China. Global Strategy Planning: For businesses, understanding geographic revenue distribution can help in developing regional strategies and identifying new opportunities for expansion. This API offers a granular view of regional revenue, making it easier to track a company&rsquo;s global financial performance. Example Use Case An investor can use the Revenue Geographic Segments API to track Apple&rsquo;s performance across key regions like the Americas, Europe, and Greater China, helping to identify emerging markets or regions with declining sales.

**Endpoint:** `https://financialmodelingprep.com/stable/revenue-geographic-segmentation?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| period | string | annual,quarter |
| structure | string | flat |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "fiscalYear": 2024,
    "period": "FY",
    "reportedCurrency": null,
    "date": "2024-09-28",
    "data": {
      "Americas Segment": 167045000000,
      "Europe Segment": 101328000000,
      "Greater China Segment": 66952000000,
      "Japan Segment": 25052000000,
      "Rest of Asia Pacific": 30658000000
    }
  }
]
```

---

## As Reported

### As Reported Income Statements

Retrieve income statements as they were reported by the company with the As Reported Income Statements API. Access raw financial data directly from official company filings, including revenue, expenses, and net income.

The As Reported Income Statements API provides a clear and direct view of a company's financial performance as reported in their official financial statements. This API is useful for: Direct Financial Insights: Access income statement data as reported by the company, without adjustments. Comprehensive Expense Tracking: See detailed breakdowns of revenue, cost of goods sold, and operating expenses. In-Depth Analysis: Use the raw data to perform your own calculations and build models based on official figures. This API allows investors and analysts to rely on the most accurate, company-provided financial information for evaluating profitability and operational efficiency. Example Use Case A financial analyst can use the As Reported Income Statements API to access Apple&rsquo;s quarterly income statements, allowing them to compare operating income and net profit for different fiscal periods without any adjustments.

**Endpoint:** `https://financialmodelingprep.com/stable/income-statement-as-reported?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |
| period | string | annual,quarter |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "fiscalYear": 2024,
    "period": "FY",
    "reportedCurrency": null,
    "date": "2024-09-27",
    "data": {
      "revenuefromcontractwithcustomerexcludingassessedtax": 391035000000,
      "costofgoodsandservicessold": 210352000000,
      "grossprofit": 180683000000,
      "researchanddevelopmentexpense": 31370000000,
      "sellinggeneralandadministrativeexpense": 26097000000,
      "operatingexpenses": 57467000000,
      "operatingincomeloss": 123216000000,
      "nonoperatingincomeexpense": 269000000,
      "incomelossfromcontinuingoperationsbeforeincometaxesextraordinaryitemsnoncontrollinginterest": 123485000000,
      "incometaxexpensebenefit": 29749000000,
      "netincomeloss": 93736000000,
      "earningspersharebasic": 6.11,
      "earningspersharediluted": 6.08,
      "weightedaveragenumberofsharesoutstandingbasic": 15343783000,
      "weightedaveragenumberofdilutedsharesoutstanding": 15408095000,
      "othercomprehensiveincomelossforeigncurrencytransactionandtranslationadjustmentnetoftax": 395000000,
      "othercomprehensiveincomelossderivativeinstrumentgainlossbeforereclassificationaftertax": -832000000,
      "othercomprehensiveincomelossderivativeinstrumentgainlossreclassificationaftertax": 1337000000,
      "othercomprehensiveincomelossderivativeinstrumentgainlossafterreclassificationandtax": -2169000000,
      "othercomprehensiveincomeunrealizedholdinggainlossonsecuritiesarisingduringperiodnetoftax": 5850000000,
      "othercomprehensiveincomelossreclassificationadjustmentfromaociforsaleofsecuritiesnetoftax": -204000000,
      "othercomprehensiveincomelossavailableforsalesecuritiesadjustmentnetoftax": 6054000000,
      "othercomprehensiveincomelossnetoftaxportionattributabletoparent": 4280000000,
      "comprehensiveincomenetoftax": 98016000000
    }
  }
]
```

---

### As Reported Balance Statements

Access balance sheets as reported by the company with the As Reported Balance Statements API. View detailed financial data on assets, liabilities, and equity directly from official filings.

The As Reported Balance Statements API offers unadjusted balance sheet data as reported by companies. It provides insight into a company's financial position, including: Asset Overview: View cash, receivables, inventory, and long-term assets as reported. Liability Breakdown: Access current and non-current liabilities, deferred revenues, and more. Equity Insights: Examine stockholders&rsquo; equity, including retained earnings and stock details. This API is ideal for analysts and investors who want raw, as-reported balance sheet data to perform accurate financial assessments. Example Use Case An investment analyst can use the As Reported Balance Statements API to evaluate Apple's asset-liability structure for Q1 2010, helping to understand the company's financial position during that period without any adjustments.

**Endpoint:** `https://financialmodelingprep.com/stable/balance-sheet-statement-as-reported?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |
| period | string | annual,quarter |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "fiscalYear": 2024,
    "period": "FY",
    "reportedCurrency": null,
    "date": "2024-09-27",
    "data": {
      "cashandcashequivalentsatcarryingvalue": 29943000000,
      "marketablesecuritiescurrent": 35228000000,
      "accountsreceivablenetcurrent": 33410000000,
      "nontradereceivablescurrent": 32833000000,
      "inventorynet": 7286000000,
      "otherassetscurrent": 14287000000,
      "assetscurrent": 152987000000,
      "marketablesecuritiesnoncurrent": 91479000000,
      "propertyplantandequipmentnet": 45680000000,
      "otherassetsnoncurrent": 74834000000,
      "assetsnoncurrent": 211993000000,
      "assets": 364980000000,
      "accountspayablecurrent": 68960000000,
      "otherliabilitiescurrent": 78304000000,
      "contractwithcustomerliabilitycurrent": 8249000000,
      "commercialpaper": 10000000000,
      "longtermdebtcurrent": 10912000000,
      "liabilitiescurrent": 176392000000,
      "longtermdebtnoncurrent": 85750000000,
      "otherliabilitiesnoncurrent": 45888000000,
      "liabilitiesnoncurrent": 131638000000,
      "liabilities": 308030000000,
      "commonstocksharesoutstanding": 15116786000,
      "commonstocksharesissued": 15116786000,
      "commonstocksincludingadditionalpaidincapital": 83276000000,
      "retainedearningsaccumulateddeficit": -19154000000,
      "accumulatedothercomprehensiveincomelossnetoftax": -7172000000,
      "stockholdersequity": 56950000000,
      "liabilitiesandstockholdersequity": 364980000000,
      "commonstockparorstatedvaluepershare": 0.00001,
      "commonstocksharesauthorized": 50400000000
    }
  }
]
```

---

### As Reported Cashflow Statements

View cash flow statements as reported by the company with the As Reported Cash Flow Statements API. Analyze a company's cash flows related to operations, investments, and financing directly from official reports.

The As Reported Cash Flow Statements API provides access to unadjusted cash flow data as reported by companies. This includes: Operational Cash Flows: Examine the cash generated or used in day-to-day business activities. Investment Cash Flows: Access cash movements related to investments in assets, acquisitions, and securities. Financing Cash Flows: View cash from equity, debt issuance, and dividend payments. This API is ideal for users looking for a clear understanding of a company's cash flow management based on official filings. Example Use Case A financial analyst can use this API to track Apple's cash flow trends during Q1 2010, helping assess how effectively the company is managing its cash for operations and investments.

**Endpoint:** `https://financialmodelingprep.com/stable/cash-flow-statement-as-reported?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |
| period | string | annual,quarter |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "fiscalYear": 2024,
    "period": "FY",
    "reportedCurrency": null,
    "date": "2024-09-27",
    "data": {
      "cashcashequivalentsrestrictedcashandrestrictedcashequivalents": 29943000000,
      "netincomeloss": 93736000000,
      "depreciationdepletionandamortization": 11445000000,
      "sharebasedcompensation": 11688000000,
      "othernoncashincomeexpense": 2266000000,
      "increasedecreaseinaccountsreceivable": 3788000000,
      "increasedecreaseinotherreceivables": 1356000000,
      "increasedecreaseininventories": 1046000000,
      "increasedecreaseinotheroperatingassets": 11731000000,
      "increasedecreaseinaccountspayable": 6020000000,
      "increasedecreaseinotheroperatingliabilities": 15552000000,
      "netcashprovidedbyusedinoperatingactivities": 118254000000,
      "paymentstoacquireavailableforsalesecuritiesdebt": 48656000000,
      "proceedsfrommaturitiesprepaymentsandcallsofavailableforsalesecurities": 51211000000,
      "proceedsfromsaleofavailableforsalesecuritiesdebt": 11135000000,
      "paymentstoacquirepropertyplantandequipment": 9447000000,
      "paymentsforproceedsfromotherinvestingactivities": 1308000000,
      "netcashprovidedbyusedininvestingactivities": 2935000000,
      "paymentsrelatedtotaxwithholdingforsharebasedcompensation": 5600000000,
      "paymentsofdividends": 15234000000,
      "paymentsforrepurchaseofcommonstock": 94949000000,
      "repaymentsoflongtermdebt": 9958000000,
      "proceedsfromrepaymentsofcommercialpaper": 3960000000,
      "proceedsfrompaymentsforotherfinancingactivities": -361000000,
      "netcashprovidedbyusedinfinancingactivities": -121983000000,
      "cashcashequivalentsrestrictedcashandrestrictedcashequivalentsperiodincreasedecreaseincludingexchangerateeffect": -794000000,
      "incometaxespaidnet": 26102000000
    }
  }
]
```

---

### As Reported Financial Statements

Retrieve comprehensive financial statements as reported by companies with FMP Financial Raw Filings API. Access complete data across income, balance sheet, and cash flow statements in their original form for detailed analysis.

The Financial Raw Filings API provides users with original, unadjusted financial statements directly from company filings. This API is ideal for: Detailed Financial Audits: Access income, balance sheet, and cash flow statements exactly as companies report them, ensuring compliance and accuracy. Investment Analysis: Analyze reported figures to assess a company&rsquo;s financial performance over time and compare them to industry peers. Historical Data Tracking: Retrieve historical financials to track trends, identify growth opportunities, or spot potential red flags. Compliance and Reporting: Leverage raw data for audits, compliance, or regulatory filings, ensuring your records match the company&rsquo;s public disclosures. This API allows investors, auditors, and analysts to dive deep into the original financial data filed by public companies for greater accuracy and insights. Example Use Case An auditor can use the As Reported Financial Statements API to retrieve Apple's historical financials, including balance sheet, income, and cash flow data, exactly as reported to the SEC. This raw data can help verify the accuracy of an investment analysis or ensure compliance with financial reporting standards.

**Endpoint:** `https://financialmodelingprep.com/stable/financial-statement-full-as-reported?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 5 |
| period | string | annual,quarter |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "fiscalYear": 2024,
    "period": "FY",
    "reportedCurrency": null,
    "date": "2024-09-27",
    "data": {
      "documenttype": "10-K",
      "documentannualreport": "true",
      "currentfiscalyearenddate": "--09-28",
      "documentperiodenddate": "2024-09-28",
      "documenttransitionreport": "false",
      "entityfilenumber": "001-36743",
      "entityregistrantname": "Apple Inc.",
      "entityincorporationstatecountrycode": "CA",
      "entitytaxidentificationnumber": "94-2404110",
      "entityaddressaddressline1": "One Apple Park Way",
      "entityaddresscityortown": "Cupertino",
      "entityaddressstateorprovince": "CA",
      "entityaddresspostalzipcode": 95014,
      "cityareacode": 408,
      "localphonenumber": "996-1010",
      "security12btitle": "3.600% Notes due 2042",
      "tradingsymbol": "AAPL",
      "notradingsymbolflag": "true",
      "securityexchangename": "NASDAQ",
      "entitywellknownseasonedissuer": "Yes",
      "entityvoluntaryfilers": "No",
      "entitycurrentreportingstatus": "Yes",
      "entityinteractivedatacurrent": "Yes",
      "entityfilercategory": "Large Accelerated Filer",
      "entitysmallbusiness": "false",
      "entityemerginggrowthcompany": "false",
      "icfrauditorattestationflag": "true",
      "documentfinstmterrorcorrectionflag": "false",
      "entityshellcompany": "false",
      "amendmentflag": "false",
      "documentfiscalyearfocus": 2024,
      "documentfiscalperiodfocus": "FY",
      "entitycentralindexkey": 320193,
      "auditorname": "Ernst & Young LLP",
      "auditorlocation": "San Jose, California",
      "auditorfirmid": 42,
      "revenuefromcontractwithcustomerexcludingassessedtax": 391035000000,
      "costofgoodsandservicessold": 210352000000,
      "grossprofit": 180683000000,
      "researchanddevelopmentexpense": 31370000000,
      "sellinggeneralandadministrativeexpense": 26097000000,
      "operatingexpenses": 57467000000,
      "operatingincomeloss": 123216000000,
      "nonoperatingincomeexpense": 269000000,
      "incomelossfromcontinuingoperationsbeforeincometaxesextraordinaryitemsnoncontrollinginterest": 123485000000,
      "incometaxexpensebenefit": 29749000000,
      "netincomeloss": 93736000000,
      "earningspersharebasic": 6.11,
      "earningspersharediluted": 6.08,
      "weightedaveragenumberofsharesoutstandingbasic": 15343783000,
      "weightedaveragenumberofdilutedsharesoutstanding": 15408095000,
      "othercomprehensiveincomelossforeigncurrencytransactionandtranslationadjustmentnetoftax": 395000000,
      "othercomprehensiveincomelossderivativeinstrumentgainlossbeforereclassificationaftertax": -832000000,
      "othercomprehensiveincomelossderivativeinstrumentgainlossreclassificationaftertax": 1337000000,
      "othercomprehensiveincomelossderivativeinstrumentgainlossafterreclassificationandtax": -2169000000,
      "othercomprehensiveincomeunrealizedholdinggainlossonsecuritiesarisingduringperiodnetoftax": 5850000000,
      "othercomprehensiveincomelossreclassificationadjustmentfromaociforsaleofsecuritiesnetoftax": -204000000,
      "othercomprehensiveincomelossavailableforsalesecuritiesadjustmentnetoftax": 6054000000,
      "othercomprehensiveincomelossnetoftaxportionattributabletoparent": 4280000000,
      "comprehensiveincomenetoftax": 98016000000,
      "cashandcashequivalentsatcarryingvalue": 29943000000,
      "marketablesecuritiescurrent": 35228000000,
      "accountsreceivablenetcurrent": 33410000000,
      "nontradereceivablescurrent": 32833000000,
      "inventorynet": 7286000000,
      "otherassetscurrent": 14287000000,
      "assetscurrent": 152987000000,
      "marketablesecuritiesnoncurrent": 91479000000,
      "propertyplantandequipmentnet": 45680000000,
      "otherassetsnoncurrent": 74834000000,
      "assetsnoncurrent": 211993000000,
      "assets": 364980000000,
      "accountspayablecurrent": 68960000000,
      "otherliabilitiescurrent": 78304000000,
      "contractwithcustomerliabilitycurrent": 8249000000,
      "commercialpaper": 10000000000,
      "longtermdebtcurrent": 10912000000,
      "liabilitiescurrent": 176392000000,
      "longtermdebtnoncurrent": 85750000000,
      "otherliabilitiesnoncurrent": 45888000000,
      "liabilitiesnoncurrent": 131638000000,
      "liabilities": 308030000000,
      "commonstocksharesoutstanding": 15116786000,
      "commonstocksharesissued": 15116786000,
      "commonstocksincludingadditionalpaidincapital": 83276000000,
      "retainedearningsaccumulateddeficit": -19154000000,
      "accumulatedothercomprehensiveincomelossnetoftax": -7172000000,
      "stockholdersequity": 56950000000,
      "liabilitiesandstockholdersequity": 364980000000,
      "commonstockparorstatedvaluepershare": 0.00001,
      "commonstocksharesauthorized": 50400000000,
      "stockissuedduringperiodvaluenewissues": 1423000000,
      "adjustmentsrelatedtotaxwithholdingforsharebasedcompensation": 1612000000,
      "adjustmentstoadditionalpaidincapitalsharebasedcompensationrequisiteserviceperiodrecognitionvalue": 12034000000,
      "dividends": 15218000000,
      "stockrepurchasedandretiredduringperiodvalue": 95000000000,
      "commonstockdividendspersharedeclared": 0.98,
      "cashcashequivalentsrestrictedcashandrestrictedcashequivalents": 29943000000,
      "depreciationdepletionandamortization": 11445000000,
      "sharebasedcompensation": 11688000000,
      "othernoncashincomeexpense": 2266000000,
      "increasedecreaseinaccountsreceivable": 3788000000,
      "increasedecreaseinotherreceivables": 1356000000,
      "increasedecreaseininventories": 1046000000,
      "increasedecreaseinotheroperatingassets": 11731000000,
      "increasedecreaseinaccountspayable": 6020000000,
      "increasedecreaseinotheroperatingliabilities": 15552000000,
      "netcashprovidedbyusedinoperatingactivities": 118254000000,
      "paymentstoacquireavailableforsalesecuritiesdebt": 48656000000,
      "proceedsfrommaturitiesprepaymentsandcallsofavailableforsalesecurities": 51211000000,
      "proceedsfromsaleofavailableforsalesecuritiesdebt": 11135000000,
      "paymentstoacquirepropertyplantandequipment": 9447000000,
      "paymentsforproceedsfromotherinvestingactivities": 1308000000,
      "netcashprovidedbyusedininvestingactivities": 2935000000,
      "paymentsrelatedtotaxwithholdingforsharebasedcompensation": 5600000000,
      "paymentsofdividends": 15234000000,
      "paymentsforrepurchaseofcommonstock": 94949000000,
      "repaymentsoflongtermdebt": 9958000000,
      "proceedsfromrepaymentsofcommercialpaper": 3960000000,
      "proceedsfrompaymentsforotherfinancingactivities": -361000000,
      "netcashprovidedbyusedinfinancingactivities": -121983000000,
      "cashcashequivalentsrestrictedcashandrestrictedcashequivalentsperiodincreasedecreaseincludingexchangerateeffect": -794000000,
      "incometaxespaidnet": 26102000000,
      "commercialpapercashflowsummarytabletextblock": "The following table provides a summary of cash flows associated with the issuance and maturities of commercial paper for 2024, 2023 and 2022 (in millions):",
      "contractwithcustomerliabilityrevenuerecognized": 7700000000,
      "contractwithcustomerliability": 12800000000,
      "revenueremainingperformanceobligationpercentage": 0.02,
      "revenueremainingperformanceobligationexpectedtimingofsatisfactionperiod1": "P1Y",
      "incrementalcommonsharesattributabletosharebasedpaymentarrangements": 64312000,
      "cash": 27199000000,
      "equitysecuritiesfvnicost": 1293000000,
      "equitysecuritiesfvniaccumulatedgrossunrealizedgainbeforetax": 105000000,
      "equitysecuritiesfvniaccumulatedgrossunrealizedlossbeforetax": 3000000,
      "equitysecuritiesfvnicurrentandnoncurrent": 1395000000,
      "availableforsaledebtsecuritiesamortizedcostbasis": 132108000000,
      "availableforsaledebtsecuritiesaccumulatedgrossunrealizedgainbeforetax": 583000000,
      "availableforsaledebtsecuritiesaccumulatedgrossunrealizedlossbeforetax": 4635000000,
      "availableforsalesecuritiesdebtsecurities": 128056000000,
      "cashcashequivalentsandmarketablesecuritiescost": 160600000000,
      "cashequivalentsandmarketablesecuritiesaccumulatedgrossunrealizedgainbeforetax": 688000000,
      "cashequivalentsandmarketablesecuritiesaccumulatedgrossunrealizedlossbeforetax": 4638000000,
      "cashcashequivalentsandmarketablesecurities": 156650000000,
      "restrictedcashandcashequivalents": 2600000000,
      "debtsecuritiesavailableforsalerestricted": 13200000000,
      "debtsecuritiesavailableforsalematurityallocatedandsinglematuritydaterollingafteronethroughfiveyearspercentage": 0.14,
      "debtsecuritiesavailableforsalematurityallocatedandsinglematuritydaterollingafterfivethroughtenyearspercentage": 0.09,
      "debtsecuritiesavailableforsalematurityallocatedandsinglematuritydaterollingaftertenyearspercentage": 0.77,
      "maximumlengthoftimeforeigncurrencycashflowhedge": "P18Y",
      "concentrationriskpercentage1": 0.23,
      "numberofsignificantvendors": 2,
      "derivativenotionalamount": 91493000000,
      "hedgedassetstatementoffinancialpositionextensibleenumeration": "http://fasb.org/us-gaap/2024#MarketableSecuritiesCurrent http://fasb.org/us-gaap/2024#MarketableSecuritiesNoncurrent",
      "hedgedliabilityfairvaluehedge": 13505000000,
      "hedgedliabilitystatementoffinancialpositionextensibleenumeration": "http://fasb.org/us-gaap/2024#LongTermDebtCurrent http://fasb.org/us-gaap/2024#LongTermDebtNoncurrent",
      "propertyplantandequipmentgross": 119128000000,
      "accumulateddepreciationdepletionandamortizationpropertyplantandequipment": 73448000000,
      "depreciation": 8200000000,
      "deferredincometaxassetsnet": 19499000000,
      "otherassetsmiscellaneousnoncurrent": 55335000000,
      "accruedincometaxescurrent": 1200000000,
      "otheraccruedliabilitiescurrent": 51703000000,
      "accruedincometaxesnoncurrent": 9254000000,
      "otheraccruedliabilitiesnoncurrent": 36634000000,
      "totalrestrictedcashcashequivalentsandavailableforsaledebtsecurities": 15800000000,
      "currentforeigntaxexpensebenefit": 25483000000,
      "currentfederaltaxexpensebenefit": 5571000000,
      "unrecognizedtaxbenefitsdecreasesresultingfromsettlementswithtaxingauthorities": 1070000000,
      "incomelossfromcontinuingoperationsbeforeincometaxesforeign": 77300000000,
      "effectiveincometaxratereconciliationatfederalstatutoryincometaxrate": 0.21,
      "deferredtaxassetstaxcreditcarryforwardsforeign": 5100000000,
      "deferredtaxassetstaxcreditcarryforwardsresearch": 3600000000,
      "unrecognizedtaxbenefits": 22038000000,
      "unrecognizedtaxbenefitsthatwouldimpacteffectivetaxrate": 10800000000,
      "decreaseinunrecognizedtaxbenefitsisreasonablypossible": 13000000000,
      "deferredfederalincometaxexpensebenefit": -3080000000,
      "federalincometaxexpensebenefitcontinuingoperations": 2491000000,
      "currentstateandlocaltaxexpensebenefit": 1726000000,
      "deferredstateandlocalincometaxexpensebenefit": -298000000,
      "stateandlocalincometaxexpensebenefitcontinuingoperations": 1428000000,
      "deferredforeignincometaxexpensebenefit": 347000000,
      "foreignincometaxexpensebenefitcontinuingoperations": 25830000000,
      "incometaxreconciliationincometaxexpensebenefitatfederalstatutoryincometaxrate": 25932000000,
      "incometaxreconciliationstateandlocalincometaxes": 1162000000,
      "effectiveincometaxratereconciliationimpactofthestateaiddecisionamount": 10246000000,
      "incometaxreconciliationforeignincometaxratedifferential": -5311000000,
      "incometaxreconciliationtaxcreditsresearch": 1397000000,
      "effectiveincometaxratereconciliationsharebasedcompensationexcesstaxbenefitamount": -893000000,
      "incometaxreconciliationotheradjustments": 10000000,
      "effectiveincometaxratecontinuingoperations": 0.241,
      "deferredtaxassetscapitalizedresearchanddevelopment": 10739000000,
      "deferredtaxassetstaxcreditcarryforwards": 8856000000,
      "deferredtaxassetstaxdeferredexpensereservesandaccruals": 6114000000,
      "deferredtaxassetsdeferredincome": 3413000000,
      "deferredtaxassetsleaseliabilities": 2410000000,
      "deferredtaxassetsothercomprehensiveloss": 1173000000,
      "deferredtaxassetsother": 2168000000,
      "deferredtaxassetsgross": 34873000000,
      "deferredtaxassetsvaluationallowance": 8866000000,
      "deferredtaxassetsnet": 26007000000,
      "deferredtaxliabilitiespropertyplantandequipment": 2551000000,
      "deferredtaxliabilitiesleasingarrangements": 2125000000,
      "deferredtaxliabilitiesminimumtaxonforeignearnings": 1674000000,
      "deferredtaxliabilitiesother": 455000000,
      "deferredincometaxliabilities": 6805000000,
      "deferredtaxassetsliabilitiesnet": 19202000000,
      "unrecognizedtaxbenefitsincreasesresultingfrompriorperiodtaxpositions": 1727000000,
      "unrecognizedtaxbenefitsdecreasesresultingfrompriorperiodtaxpositions": 386000000,
      "unrecognizedtaxbenefitsincreasesresultingfromcurrentperiodtaxpositions": 2542000000,
      "unrecognizedtaxbenefitsreductionsresultingfromlapseofapplicablestatuteoflimitations": 229000000,
      "lesseeoperatingandfinanceleasetermofcontract": "P10Y",
      "operatingleasecost": 2000000000,
      "variableleasecost": 13800000000,
      "operatingleasepayments": 1900000000,
      "rightofuseassetsobtainedinexchangeforoperatingandfinanceleaseliabilities": 1000000000,
      "operatingandfinanceleaseweightedaverageremainingleaseterm": "P10Y3M18D",
      "operatingandfinanceleaseweightedaveragediscountratepercent": 0.031,
      "unrecordedunconditionalpurchaseobligationbalancesheetamount": 11226000000,
      "lesseeoperatingandfinanceleaseleasenotyetcommencedtermofcontract": "P21Y",
      "operatingleaserightofuseasset": 10234000000,
      "operatingleaserightofuseassetstatementoffinancialpositionextensiblelist": "http://fasb.org/us-gaap/2024#OtherAssetsNoncurrent",
      "financeleaserightofuseasset": 1069000000,
      "financeleaserightofuseassetstatementoffinancialpositionextensiblelist": "http://fasb.org/us-gaap/2024#PropertyPlantAndEquipmentNet",
      "operatingandfinanceleaserightofuseasset": 11303000000,
      "operatingleaseliabilitycurrent": 1488000000,
      "operatingleaseliabilitycurrentstatementoffinancialpositionextensiblelist": "http://fasb.org/us-gaap/2024#OtherLiabilitiesCurrent",
      "operatingleaseliabilitynoncurrent": 10046000000,
      "operatingleaseliabilitynoncurrentstatementoffinancialpositionextensiblelist": "http://fasb.org/us-gaap/2024#OtherLiabilitiesNoncurrent",
      "financeleaseliabilitycurrent": 144000000,
      "financeleaseliabilitycurrentstatementoffinancialpositionextensiblelist": "http://fasb.org/us-gaap/2024#OtherLiabilitiesCurrent",
      "financeleaseliabilitynoncurrent": 752000000,
      "financeleaseliabilitynoncurrentstatementoffinancialpositionextensiblelist": "http://fasb.org/us-gaap/2024#OtherLiabilitiesNoncurrent",
      "operatingandfinanceleaseliability": 12430000000,
      "lesseeoperatingleaseliabilitypaymentsduenexttwelvemonths": 1820000000,
      "lesseeoperatingleaseliabilitypaymentsdueyeartwo": 1914000000,
      "lesseeoperatingleaseliabilitypaymentsdueyearthree": 1674000000,
      "lesseeoperatingleaseliabilitypaymentsdueyearfour": 1360000000,
      "lesseeoperatingleaseliabilitypaymentsdueyearfive": 1187000000,
      "lesseeoperatingleaseliabilitypaymentsdueafteryearfive": 5563000000,
      "lesseeoperatingleaseliabilitypaymentsdue": 13518000000,
      "lesseeoperatingleaseliabilityundiscountedexcessamount": 1984000000,
      "operatingleaseliability": 11534000000,
      "financeleaseliabilitypaymentsduenexttwelvemonths": 171000000,
      "financeleaseliabilitypaymentsdueyeartwo": 131000000,
      "financeleaseliabilitypaymentsdueyearthree": 59000000,
      "financeleaseliabilitypaymentsdueyearfour": 38000000,
      "financeleaseliabilitypaymentsdueyearfive": 36000000,
      "financeleaseliabilitypaymentsdueafteryearfive": 837000000,
      "financeleaseliabilitypaymentsdue": 1272000000,
      "financeleaseliabilityundiscountedexcessamount": 376000000,
      "financeleaseliability": 896000000,
      "lesseeoperatingandfinanceleaseliabilitytobepaidyearone": 1991000000,
      "lesseeoperatingandfinanceleaseliabilitytobepaidyeartwo": 2045000000,
      "lesseeoperatingandfinanceleaseliabilitytobepaidyearthree": 1733000000,
      "lesseeoperatingandfinanceleaseliabilitytobepaidyearfour": 1398000000,
      "lesseeoperatingandfinanceleaseliabilitytobepaidyearfive": 1223000000,
      "lesseeoperatingandfinanceleaseliabilitytobepaidafteryearfive": 6400000000,
      "lesseeoperatingandfinanceleaseliabilitytobepaid": 14790000000,
      "lesseeoperatingandfinanceleaseliabilityundiscountedexcessamount": 2360000000,
      "debtinstrumentterm": "P9M",
      "shorttermdebtweightedaverageinterestrate": 0.05,
      "longtermdebtfairvalue": 88400000000,
      "proceedsfromrepaymentsofshorttermdebtmaturinginthreemonthsorless": 3960000000,
      "debtinstrumentcarryingamount": 97341000000,
      "debtinstrumentunamortizeddiscountpremiumanddebtissuancecostsnet": 321000000,
      "hedgeaccountingadjustmentsrelatedtolongtermdebt": 358000000,
      "longtermdebt": 96662000000,
      "debtinstrumentmaturityyearrangestart": 2024,
      "debtinstrumentmaturityyearrangeend": 2062,
      "debtinstrumentinterestratestatedpercentage": 0.0485,
      "debtinstrumentinterestrateeffectivepercentage": 0.0665,
      "longtermdebtmaturitiesrepaymentsofprincipalinnexttwelvemonths": 10930000000,
      "longtermdebtmaturitiesrepaymentsofprincipalinyeartwo": 12342000000,
      "longtermdebtmaturitiesrepaymentsofprincipalinyearthree": 9936000000,
      "longtermdebtmaturitiesrepaymentsofprincipalinyearfour": 7800000000,
      "longtermdebtmaturitiesrepaymentsofprincipalinyearfive": 5153000000,
      "longtermdebtmaturitiesrepaymentsofprincipalafteryearfive": 51180000000,
      "stockrepurchasedandretiredduringperiodshares": 499372000,
      "stockissuedduringperiodsharessharebasedpaymentarrangementnetofshareswithheldfortaxes": 66097000,
      "sharebasedcompensationarrangementbysharebasedpaymentawardawardvestingperiod1": "P4Y",
      "sharebasedcompensationarrangementbysharebasedpaymentawardequityinstrumentsotherthanoptionsnumberofsharesofcommonstockissuedperunituponvesting": 1,
      "sharebasedcompensationarrangementbysharebasedpaymentawardequityinstrumentsotherthanoptionsvestedinperiodtotalfairvalue": 15800000000,
      "sharespaidfortaxwithholdingforsharebasedcompensation": 31000000,
      "employeeservicesharebasedcompensationnonvestedawardstotalcompensationcostnotyetrecognized": 19400000000,
      "employeeservicesharebasedcompensationnonvestedawardstotalcompensationcostnotyetrecognizedperiodforrecognition1": "P2Y4M24D",
      "sharebasedcompensationarrangementbysharebasedpaymentawardequityinstrumentsotherthanoptionsnonvestednumber": 163326000,
      "sharebasedcompensationarrangementbysharebasedpaymentawardequityinstrumentsotherthanoptionsgrantsinperiod": 80456000,
      "sharebasedcompensationarrangementbysharebasedpaymentawardequityinstrumentsotherthanoptionsvestedinperiod": 87633000,
      "sharebasedcompensationarrangementbysharebasedpaymentawardequityinstrumentsotherthanoptionsforfeitedinperiod": 9744000,
      "sharebasedcompensationarrangementbysharebasedpaymentawardequityinstrumentsotherthanoptionsnonvestedweightedaveragegrantdatefairvalue": 158.73,
      "sharebasedcompensationarrangementbysharebasedpaymentawardequityinstrumentsotherthanoptionsgrantsinperiodweightedaveragegrantdatefairvalue": 173.78,
      "sharebasedcompensationarrangementbysharebasedpaymentawardequityinstrumentsotherthanoptionsvestedinperiodweightedaveragegrantdatefairvalue": 127.59,
      "sharebasedcompensationarrangementbysharebasedpaymentawardequityinstrumentsotherthanoptionsforfeituresweightedaveragegrantdatefairvalue": 140.8,
      "sharebasedcompensationarrangementbysharebasedpaymentawardequityinstrumentsotherthanoptionsaggregateintrinsicvaluenonvested": 37204000000,
      "allocatedsharebasedcompensationexpense": 11688000000,
      "employeeservicesharebasedcompensationtaxbenefitfromcompensationexpense": 3350000000,
      "unrecordedunconditionalpurchaseobligationbalanceonfirstanniversary": 3206000000,
      "unrecordedunconditionalpurchaseobligationbalanceonsecondanniversary": 2440000000,
      "unrecordedunconditionalpurchaseobligationbalanceonthirdanniversary": 1156000000,
      "unrecordedunconditionalpurchaseobligationbalanceonfourthanniversary": 3121000000,
      "unrecordedunconditionalpurchaseobligationbalanceonfifthanniversary": 633000000,
      "unrecordedunconditionalpurchaseobligationdueafterfiveyears": 670000000,
      "othergeneralandadministrativeexpense": 7458000000,
      "noncurrentassets": 45680000000,
      "trdarrsecuritiesaggavailamt": 100000,
      "insidertrdpoliciesprocadoptedflag": "true"
    }
  }
]
```

---

# Form13F

## Extract

### Institutional Ownership Filings

Stay up to date with the most recent SEC filings related to institutional ownership using the Institutional Ownership Filings API. This tool allows you to track the latest reports and disclosures from institutional investors, giving you a real-time view of major holdings and regulatory submissions.

The Institutional Ownership Filings API gives access to the latest SEC filings from institutional investors, providing insights into reports like Form 13F filings. It&rsquo;s perfect for staying on top of which institutions hold shares in specific companies and monitoring significant ownership changes. This API is ideal for: Tracking Institutional Ownership: Stay updated on which institutions hold shares in specific companies. Monitoring Investor Activity: Access filings that show when large investors are buying or selling shares. Research &amp; Analysis: Use this data for investment research and trend analysis to see which institutions are bullish or bearish on a company. Compliance &amp; Governance: Utilize filings to ensure corporate actions comply with regulatory requirements. This API ensures real-time access to the most recent institutional filings, keeping you informed about significant investor movements. Example Use Case An investment researcher can use the Institutional Ownership Filings API to monitor changes in institutional ownership for companies like Apple, identifying when major hedge funds or pension funds increase or decrease their stakes.

**Endpoint:** `https://financialmodelingprep.com/stable/institutional-ownership/latest?page=0&limit=100`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| page | number | 0 |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "cik": "0001686970",
    "name": "ODDO BHF ASSET MANAGEMENT SAS",
    "date": "2025-03-31",
    "filingDate": "2026-06-05 00:00:00",
    "acceptedDate": "2026-06-05 11:45:56",
    "formType": "13F-HR/A",
    "link": "https://www.sec.gov/Archives/edgar/data/1686970/000168697026000003/0001686970-26-000003-index.htm",
    "finalLink": "https://www.sec.gov/Archives/edgar/data/1686970/000168697026000003/xml.xml"
  }
]
```

---

### Filings Extract

The SEC Filings Extract API allows users to extract detailed data directly from official SEC filings. This API provides access to key information such as company shares, security details, and filing links, making it easier to analyze corporate disclosures.

The SEC Filings Extract API offers a streamlined way to retrieve detailed information from SEC filings. This is ideal for investors, analysts, and financial professionals who need to analyze official company reports and gain insights into ownership structures, security details, and other critical data. This API is perfect for: SEC Filings Analysis: Extract key information from SEC filings, such as shares owned, value, and security details. Ownership Tracking: Monitor changes in company ownership over time by accessing filed reports. Filing Comparison: Compare detailed data from different filing periods to track trends and changes. This API provides a structured and simplified way to access complex SEC filings data, helping you save time and focus on the analysis. Example Use Case An investment firm uses the SEC Filings Extract API to track changes in ownership for a specific company by extracting data from quarterly 13F filings. This helps the firm identify trends and adjust its investment strategy accordingly.

**Endpoint:** `https://financialmodelingprep.com/stable/institutional-ownership/extract?cik=0001388838&year=2023&quarter=3`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| cik* | string | 0001388838 |
| year* | string | 2023 |
| quarter* | string | 3 |

**Example Response**

```json
[
  {
    "date": "2023-09-30",
    "filingDate": "2023-11-13",
    "acceptedDate": "2023-11-13",
    "cik": "0001388838",
    "securityCusip": "674215207",
    "symbol": "CHRD",
    "nameOfIssuer": "CHORD ENERGY CORPORATION",
    "shares": 13280,
    "titleOfClass": "COM NEW",
    "sharesType": "SH",
    "putCallShare": "",
    "value": 2152290,
    "link": "https://www.sec.gov/Archives/edgar/data/1388838/000117266123003760/0001172661-23-003760-index.htm",
    "finalLink": "https://www.sec.gov/Archives/edgar/data/1388838/000117266123003760/infotable.xml"
  }
]
```

---

### Form 13F Filings Dates

The Form 13F Filings Dates API allows you to retrieve dates associated with Form 13F filings by institutional investors. This is crucial for tracking stock holdings of institutional investors at specific points in time, providing valuable insights into their investment strategies.

The Form 13F Filings Dates API is ideal for users interested in tracking when institutional investors file Form 13F reports with the SEC. This data reveals their stock holdings and investment trends, helping investors and analysts understand what major institutions are investing in during specific quarters. This API is perfect for: Investor Monitoring: Track when institutional investors file their stock holdings with the SEC. Quarterly Analysis: Review changes in institutional holdings across different quarters. Historical Research: Analyze filing patterns over the years and spot trends in institutional ownership. This API provides a streamlined way to track the timing of institutional holdings, which is useful for investment analysis and understanding market trends. Example Use Case An analyst can use the Form 13F Filings Dates API to check the filing dates of a major institutional investor, allowing them to compare portfolio changes from quarter to quarter and make informed decisions based on institutional behavior.

**Endpoint:** `https://financialmodelingprep.com/stable/institutional-ownership/dates?cik=0001067983`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| cik* | string | 0001067983 |

**Example Response**

```json
[
  {
    "date": "2026-03-31",
    "year": 2026,
    "quarter": 1
  }
]
```

---

## Holder

### Filings Extract With Analytics By Holder

The Filings Extract With Analytics By Holder API provides an analytical breakdown of institutional filings. This API offers insight into stock movements, strategies, and portfolio changes by major institutional holders, helping you understand their investment behavior and track significant changes in stock ownership.

The Filings Extract With Analytics By Holder API allows users to extract detailed analytics from filings by institutional investors. It offers information such as shares held, changes in stock weight and market value, ownership percentages, and other important metrics that provide an analytical view of institutional investment strategies. Institutional Investor Analysis: Track the behavior of large institutional holders such as Vanguard, including their changes in stock positions and market value. Portfolio Movement Monitoring: Analyze stock movements and holding period data to see how long institutions have held a stock and when they increased or reduced their positions. Investment Strategy Insights: Understand investment strategies by looking at changes in weight, market value, and ownership over time. This API offers granular insights into how institutions manage their portfolios, providing data to investors and analysts for deeper investment analysis. Example Use Case An investment analyst can use the Filings Extract With Analytics By Holder API to monitor Vanguard Group's activity in Apple Inc. stocks, seeing how much stock Vanguard holds, any changes in weight or market value, and when the stock was first added to their portfolio.

**Endpoint:** `https://financialmodelingprep.com/stable/institutional-ownership/extract-analytics/holder?symbol=AAPL&year=2023&quarter=3&page=0&limit=10`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| year* | string | 2023 |
| quarter* | string | 3 |
| page | number | 0 |
| limit | number | 10 |

**Example Response**

```json
[
  {
    "date": "2023-09-30",
    "cik": "0000102909",
    "filingDate": "2023-12-18",
    "investorName": "VANGUARD GROUP INC",
    "symbol": "AAPL",
    "securityName": "APPLE INC",
    "typeOfSecurity": "COM",
    "securityCusip": "037833100",
    "sharesType": "SH",
    "putCallShare": "Share",
    "investmentDiscretion": "SOLE",
    "industryTitle": "ELECTRONIC COMPUTERS",
    "weight": 5.4673,
    "lastWeight": 5.996,
    "changeInWeight": -0.5287,
    "changeInWeightPercentage": -8.8175,
    "marketValue": 222572509140,
    "lastMarketValue": 252876459509,
    "changeInMarketValue": -30303950369,
    "changeInMarketValuePercentage": -11.9837,
    "sharesNumber": 1299997133,
    "lastSharesNumber": 1303688506,
    "changeInSharesNumber": -3691373,
    "changeInSharesNumberPercentage": -0.2831,
    "quarterEndPrice": 171.21,
    "avgPricePaid": 20.65,
    "isNew": false,
    "isSoldOut": false,
    "ownership": 8.3336,
    "lastOwnership": 8.305,
    "changeInOwnership": 0.0286,
    "changeInOwnershipPercentage": 0.3445,
    "holdingPeriod": 75,
    "firstAdded": "2005-03-31",
    "performance": -29671950396,
    "performancePercentage": -11.7338,
    "lastPerformance": 38078179274,
    "changeInPerformance": -67750129670,
    "isCountedForPerformance": true
  }
]
```

---

### Holder Performance Summary

The Holder Performance Summary API provides insights into the performance of institutional investors based on their stock holdings. This data helps track how well institutional holders are performing, their portfolio changes, and how their performance compares to benchmarks like the S&P 500.

The Holder Performance Summary API allows users to view performance metrics for institutional holders, such as market value changes, portfolio turnover, and relative performance against benchmarks. This API is ideal for: Institutional Investor Analysis: Track how well institutional investors are performing based on stock picks, changes in holdings, and market value. Portfolio Turnover Analysis: See how frequently an institution buys or sells securities, providing insights into their trading strategy. Performance Benchmarking: Compare an institution's performance against the S&amp;P 500 and other benchmarks over different timeframes (1 year, 3 years, 5 years). This API offers a comprehensive view of an institutional holder&rsquo;s performance over time, helping investors and analysts track key players in the market. Example Use Case An investment manager can use the Holder Performance Summary API to analyze Berkshire Hathaway's performance over the last five years and compare it to the S&amp;P 500, assessing how well their investment strategy has fared.

**Endpoint:** `https://financialmodelingprep.com/stable/institutional-ownership/holder-performance-summary?cik=0001067983&page=0`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| cik* | string | 0001067983 |
| page | number | 0 |

**Example Response**

```json
[
  {
    "date": "2026-03-31",
    "cik": "0001067983",
    "investorName": "BERKSHIRE HATHAWAY INC",
    "portfolioSize": 29,
    "securitiesAdded": 3,
    "securitiesRemoved": 16,
    "marketValue": 263095703570,
    "previousMarketValue": 274160086701,
    "changeInMarketValue": -11064383131,
    "changeInMarketValuePercentage": -4.0357,
    "averageHoldingPeriod": 19,
    "averageHoldingPeriodTop10": 32,
    "averageHoldingPeriodTop20": 25,
    "turnover": 0.6552,
    "turnoverAlternateSell": 9.1727,
    "turnoverAlternateBuy": 5.8198,
    "performance": -2243708176,
    "performancePercentage": -0.8184,
    "lastPerformance": 12155137983,
    "changeInPerformance": -14398846159,
    "performance1year": 28972344227,
    "performancePercentage1year": 11.3876,
    "performance3year": 118145980011,
    "performancePercentage3year": 45.901,
    "performance5year": 146868211621,
    "performancePercentage5year": 63.1846,
    "performanceSinceInception": 267098327593,
    "performanceSinceInceptionPercentage": 203.038,
    "performanceRelativeToSP500Percentage": 3.8118,
    "performance1yearRelativeToSP500Percentage": -4.9473,
    "performance3yearRelativeToSP500Percentage": -12.9707,
    "performance5yearRelativeToSP500Percentage": -1.1424,
    "performanceSinceInceptionRelativeToSP500Percentage": -114.8762
  }
]
```

---

### Holders Industry Breakdown

The Holders Industry Breakdown API provides an overview of the sectors and industries that institutional holders are investing in. This API helps analyze how institutional investors distribute their holdings across different industries and track changes in their investment strategies over time.

The Holders Industry Breakdown API allows users to retrieve data on the industries institutional investors are focusing on, including the weight of their holdings in each sector and how that weight changes over time. This API provides detailed insights into the industry allocation of institutional investors, making it easier to understand their sector focus and strategy. Industry Focus Analysis: Understand which industries are receiving the most investment from major institutional holders. Portfolio Diversification: Analyze how diversified institutional investors' portfolios are across different sectors. Investment Trend Insights: Track changes in the weight of industry holdings to identify shifts in institutional investment strategies. This API is ideal for investors, analysts, and portfolio managers looking to gain insights into institutional investment behavior across various industries. Example Use Case A financial analyst can use the Holders Industry Breakdown API to analyze Berkshire Hathaway's sector focus, identifying whether they are increasing or decreasing their exposure to industries like technology or healthcare over time.

**Endpoint:** `https://financialmodelingprep.com/stable/institutional-ownership/holder-industry-breakdown?cik=0001067983&year=2023&quarter=3`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| cik* | string | 0001067983 |
| year* | string | 2023 |
| quarter* | string | 3 |

**Example Response**

```json
[
  {
    "date": "2023-09-30",
    "cik": "0001067983",
    "investorName": "BERKSHIRE HATHAWAY INC",
    "industryTitle": "ELECTRONIC COMPUTERS",
    "weight": 49.7704,
    "lastWeight": 51.0035,
    "changeInWeight": -1.2332,
    "changeInWeightPercentage": -2.4178,
    "performance": -20838154294,
    "performancePercentage": -178.2938,
    "lastPerformance": 26615340304,
    "changeInPerformance": -47453494598
  }
]
```

---

## Symbol

### Positions Summary

The Positions Summary API provides a comprehensive snapshot of institutional holdings for a specific stock symbol. It tracks key metrics like the number of investors holding the stock, changes in the number of shares, total investment value, and ownership percentages over time.

The Positions Summary API enables users to analyze institutional positions in a particular stock by providing data such as the number of investors holding the stock, the number of shares held, the total amount invested, and changes in these metrics over a given time period. It is ideal for: Tracking Institutional Investment Trends: Monitor how institutional investors are changing their positions in a stock over time. Ownership Insights: Understand what percentage of a company is owned by institutional investors and how this changes. Call &amp; Put Analysis: Get insights into the put/call ratio and track options activity for institutional positions. This API is ideal for understanding institutional activity in the market and gaining insights into the behavior of major investors. It is essential for investors, analysts, and portfolio managers who want to keep a close eye on institutional movements in specific stocks. Example Use Case A hedge fund manager can use the Positions Summary API to track institutional ownership trends in Apple (AAPL), monitoring how many institutions are increasing or reducing their positions, and assessing overall market sentiment.

**Endpoint:** `https://financialmodelingprep.com/stable/institutional-ownership/symbol-positions-summary?symbol=AAPL&year=2023&quarter=3`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| year* | string | 2023 |
| quarter* | string | 3 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "cik": "0000320193",
    "date": "2023-09-30",
    "investorsHolding": 4856,
    "lastInvestorsHolding": 4798,
    "investorsHoldingChange": 58,
    "numberOf13Fshares": 9255867768,
    "lastNumberOf13Fshares": 9352605928,
    "numberOf13FsharesChange": -96738160,
    "totalInvested": 1595625709828,
    "lastTotalInvested": 1819210506516,
    "totalInvestedChange": -223584796688,
    "ownershipPercent": 59.3346,
    "lastOwnershipPercent": 59.5798,
    "ownershipPercentChange": -0.2452,
    "newPositions": 162,
    "lastNewPositions": 190,
    "newPositionsChange": -28,
    "increasedPositions": 1938,
    "lastIncreasedPositions": 1795,
    "increasedPositionsChange": 143,
    "closedPositions": 158,
    "lastClosedPositions": 122,
    "closedPositionsChange": 36,
    "reducedPositions": 2404,
    "lastReducedPositions": 2528,
    "reducedPositionsChange": -124,
    "totalCalls": 173627138,
    "lastTotalCalls": 198895582,
    "totalCallsChange": -25268444,
    "totalPuts": 192913290,
    "lastTotalPuts": 177042062,
    "totalPutsChange": 15871228,
    "putCallRatio": 1.1111,
    "lastPutCallRatio": 0.8901,
    "putCallRatioChange": 22.0952
  }
]
```

---

### Industry Performance Summary

The Industry Performance Summary API provides an overview of how various industries are performing financially. By analyzing the value of industries over a specific period, this API helps investors and analysts understand the health of entire sectors and make informed decisions about sector-based investments.

The Industry Performance Summary API enables users to retrieve financial performance summaries for specific industries. This API is ideal for: Sector Analysis: Gain insights into how industries are performing, helping you identify strong or underperforming sectors. Comparative Industry Health: Compare the financial health of different industries to assess which sectors might present better investment opportunities. Macro-Level Market Insights: Use industry-level performance data to make informed decisions about broad market trends and economic shifts. This API offers a macroeconomic view of sector performance, making it a valuable tool for financial analysts, investors, and economists looking to understand industry-specific trends. It is a key tool for understanding industry trends and comparing the financial health of various sectors in the market.

**Endpoint:** `https://financialmodelingprep.com/stable/institutional-ownership/industry-summary?year=2023&quarter=3`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| year* | string | 2023 |
| quarter* | string | 3 |

**Example Response**

```json
[
  {
    "industryTitle": "ABRASIVE, ASBESTOS & MISC NONMETALLIC MINERAL PRODS",
    "industryValue": 11031469701,
    "date": "2023-09-30"
  }
]
```

---

# Indexes

## Indexes

### Stock Market Indexes List

Retrieve a comprehensive list of stock market indexes across global exchanges using the FMP Stock Market Indexes List API. This API provides essential information such as the symbol, name, exchange, and currency for each index, helping analysts and investors keep track of various market benchmarks.

The FMP Stock Market Indexes List API allows users to access a full directory of stock market indexes from exchanges worldwide. It provides detailed information about index symbols, names, exchanges, and currencies, making it a valuable resource for tracking market performance across different regions and sectors. Key features include: Comprehensive Index Coverage: Access a wide range of indexes from major exchanges like NYSE, NASDAQ, and TSX. Global Reach: The API offers data on indexes from international markets, providing a truly global perspective. Basic Information on Each Index: Retrieve essential details such as the symbol, full name, and exchange, helping you identify the indexes relevant to your needs. Currency Information: Understand the currency in which each index is denominated, enabling more accurate analysis for global investors. This API is particularly useful for investors, analysts, and portfolio managers who need to monitor market movements across multiple regions and sectors. Example Use Case A portfolio manager building a global investment strategy can use the Stock Market Indexes List API to retrieve data on key indexes from exchanges around the world. By identifying relevant indexes in different regions, they can assess market performance and make informed decisions about asset allocation.

**Endpoint:** `https://financialmodelingprep.com/stable/index-list`

**Example Response**

```json
[
  {
    "symbol": "^TTIN",
    "name": "S&P/TSX Capped Industrials Index",
    "exchange": "TSX",
    "currency": "CAD"
  }
]
```

---

## Quotes

### Index Quote

Access real-time stock index quotes with the Stock Index Quote API. Stay updated with the latest price changes, daily highs and lows, volume, and other key metrics for major stock indices around the world.

The Stock Index Quote API provides real-time data on the performance of stock indices, offering a comprehensive view of current market conditions. This API is essential for: Tracking Market Performance: Monitor the real-time movements of key stock indices, like the S&amp;P 500 or NASDAQ, to stay informed about overall market trends. Portfolio Management: Use index data to evaluate the health of your investments relative to the broader market. Global Market Insights: Access index data across various markets and exchanges, allowing for a global market view. Day Trading: Keep track of daily price movements, highs, lows, and volumes for real-time decision-making. Example Use Case A trader could use the Stock Index Quote API to track the S&amp;P 500&rsquo;s daily performance in real-time, enabling them to make informed trading decisions based on market trends and volume.

**Endpoint:** `https://financialmodelingprep.com/stable/quote?symbol=^VIX`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | ^VIX |

**Example Response**

```json
[
  {
    "symbol": "^VIX",
    "name": "CBOE Volatility Index",
    "price": 16.37,
    "changePercentage": -5.37572,
    "change": -0.93,
    "volume": 0,
    "dayLow": 16.02,
    "dayHigh": 17.22,
    "yearHigh": 60.13,
    "yearLow": 12.7,
    "marketCap": 0,
    "priceAvg50": 16.5992,
    "priceAvg200": 19.3432,
    "exchange": "INDEX",
    "open": 17.02,
    "previousClose": 17.3,
    "timestamp": 1761336901
  }
]
```

---

### Index Short Quote

Access concise stock index quotes with the Stock Index Short Quote API. This API provides a snapshot of the current price, change, and volume for stock indexes, making it ideal for users who need a quick overview of market movements.

The Stock Index Short Quote API delivers simplified, real-time index data, offering essential metrics such as price, change, and volume. This API is a valuable tool for traders, investors, and analysts who need a quick overview of an index's current standing without unnecessary details. Key features include: Real-Time Index Data: Get current price, change, and volume for stock indexes. Simplified Data: Designed for users who need only the essential figures, providing a clear and efficient market snapshot. Wide Market Coverage: Retrieve short quotes for a wide range of global indexes. This API is perfect for traders and analysts who want to stay updated on index performance at a glance, enabling them to react quickly to market shifts. Example Use Case A trader monitoring the S&amp;P 500 throughout the trading day can use the Stock Index Short Quote API to quickly access real-time price changes, helping them make decisions on whether to buy or sell without delving into more complex data.

**Endpoint:** `https://financialmodelingprep.com/stable/quote-short?symbol=^VIX`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | ^VIX |

**Example Response**

```json
[
  {
    "symbol": "^VIX",
    "price": 16.37,
    "change": -0.93,
    "volume": 0
  }
]
```

---

### All Index Quotes

The All Index Quotes API provides real-time quotes for a wide range of stock indexes, from major market benchmarks to niche indexes. This API allows users to track market performance across multiple indexes in a single request, giving them a broad view of the financial markets.

The All Index Quotes API enables users to retrieve up-to-date quotes for all available stock indexes, including real-time data for both major and minor indexes. This API is ideal for traders, analysts, and investors who need a quick overview of market movements across various indexes without making multiple requests. Key features include: Real-Time Data: Receive real-time quotes for stock indexes, helping users stay informed about market changes. Broad Market Coverage: Access data for major indexes like the S&amp;P 500, Dow Jones, NASDAQ, and more specialized or regional indexes. Simplified Data Retrieval: Retrieve quotes for multiple indexes in a single API call, streamlining data collection for market analysis. This API is designed for users looking for a comprehensive view of stock index movements, from major global benchmarks to smaller, region-specific indexes. Example Use Case A financial analyst tracking global market performance can use the All Index Quotes API to retrieve real-time quotes for multiple stock indexes, such as the S&amp;P 500, FTSE 100, and Nikkei 225, in one request, providing a holistic view of current market trends.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-index-quotes`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| short | boolean | true |

**Example Response**

```json
[
  {
    "symbol": "XTRZM.IS",
    "price": 1997.89,
    "change": 16.17,
    "volume": 0
  }
]
```

---

## End Of Day

### Historical Index Light Chart

Retrieve end-of-day historical prices for stock indexes using the Historical Price Data API. This API provides essential data such as date, price, and volume, enabling detailed analysis of price movements over time.

The FMP Historical Price Data API allows users to access end-of-day price data for stock indexes, offering insights into historical performance. By tracking this data, analysts can better understand market trends, volatility, and stock index movements. Key features include: Comprehensive Price Data: Retrieve historical prices for key stock indexes, including data on closing price, date, and trading volume. Supports Multiple Indexes: Access data for a wide range of stock indexes from various global markets. Detailed Volume Information: Track trading volume for each index, offering insights into market activity levels. Historical Performance Analysis: Analyze past price movements to identify trends, patterns, and potential investment opportunities. This API is particularly useful for financial analysts, investors, and market researchers who need accurate historical data to assess stock index performance over time. Example Use Case An investment analyst is developing a historical trend analysis for the S&amp;P 500 index (^GSPC). By using the Historical Price Data API, they can retrieve end-of-day prices for specific dates, analyze the volume and price movements over time, and present findings to their clients for more informed investment decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/light?symbol=^VIX`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | ^VIX |
| from | date | 2026-01-27 |
| to | date | 2026-04-27 |

**Example Response**

```json
[
  {
    "symbol": "^VIX",
    "date": "2026-06-05",
    "price": 21.51,
    "volume": 0
  }
]
```

---

### Historical Index Full Chart

Access full historical end-of-day prices for stock indexes using the Detailed Historical Price Data API. This API provides comprehensive information, including open, high, low, close prices, volume, and additional metrics for detailed financial analysis.

The FMP Detailed Historical Price Data API offers full end-of-day price data for stock indexes, making it a powerful tool for in-depth financial analysis. It includes a range of price points&mdash;open, high, low, close&mdash;along with volume, price changes, and volume-weighted average price (VWAP). Key features include: Complete Price Data: Access open, high, low, and close prices for stock indexes on specific dates. Volume Information: Track trading volume to assess market activity and liquidity. Price Movement Insights: Analyze daily price changes and percentage changes to understand market trends. Volume-Weighted Average Price (VWAP): Get VWAP data for each trading day, helping in performance benchmarking and trading decisions. This API is ideal for financial analysts, quants, and traders who need comprehensive historical price data to build models, conduct backtesting, or analyze market trends. Example Use Case A quantitative analyst developing an algorithmic trading model requires complete historical price data for the S&amp;P 500 index (^GSPC). Using the Detailed Historical Price Data API, they can retrieve open, high, low, and close prices, along with VWAP and volume data for each trading day. This detailed information helps refine the model&rsquo;s predictions and backtesting performance.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=^VIX`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | ^VIX |
| from | date | 2026-01-27 |
| to | date | 2026-04-27 |

**Example Response**

```json
[
  {
    "symbol": "^VIX",
    "date": "2026-06-05",
    "open": 15.87,
    "high": 21.57,
    "low": 15.56,
    "close": 21.51,
    "volume": 0,
    "change": 5.64,
    "changePercent": 35.54,
    "vwap": 18.6275
  }
]
```

---

## Intraday

### 1-Minute Interval Index Price

Retrieve 1-minute interval intraday data for stock indexes using the Intraday 1-Minute Price Data API. This API provides granular price information, helping users track short-term price movements and trading volume within each minute.

The FMP Intraday 1-Minute Price Data API delivers high-frequency price data for stock indexes, offering insights into market fluctuations on a minute-by-minute basis. This level of detail is ideal for active traders and analysts who require real-time market insights for rapid decision-making. Key features include: Granular Price Data: Access open, high, low, and close prices for each minute of the trading day. Minute-by-Minute Tracking: Monitor short-term price movements and trends in real time. Volume Information: Analyze trading volume for each minute, offering insights into market liquidity and activity levels. Supports Intraday Trading: Perfect for day traders and high-frequency trading strategies that rely on detailed intraday data. This API is particularly useful for day traders, quants, and financial analysts who need real-time data to track rapid price movements and make timely trading decisions. Example Use Case A day trader specializing in short-term stock index trades uses the Intraday 1-Minute Price Data API to track real-time price changes in the S&amp;P 500 index (^GSPC). With access to minute-by-minute data, they can react to price movements and adjust their trading strategies in real time, optimizing their entry and exit points for maximum profitability.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1min?symbol=^VIX`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | ^VIX |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 15:59:00",
    "open": 20,
    "low": 20,
    "high": 20.18,
    "close": 20.18,
    "volume": 0
  }
]
```

---

### 5-Minute Interval Index Price

Retrieve 5-minute interval intraday price data for stock indexes using the Intraday 5-Minute Price Data API. This API provides crucial insights into price movements and trading volume within 5-minute windows, ideal for traders who require short-term data.

The FMP Intraday 5-Minute Price Data API offers real-time price and volume data for stock indexes, updated every 5 minutes during active market hours. This API is designed for traders and analysts who need detailed, short-term data to track price fluctuations and make timely decisions. Key features include: 5-Minute Interval Data: Access open, high, low, and close prices for each 5-minute interval throughout the trading day. Real-Time Tracking: Stay up-to-date with price changes and market trends in near real-time. Volume Data: Analyze trading volume in 5-minute intervals to gauge market activity and liquidity. Supports Short-Term Trading: Ideal for short-term and swing traders looking for frequent updates to inform their strategies. This API is perfect for day traders, quants, and financial professionals who need to monitor price movements closely and execute trades based on short-term fluctuations. Example Use Case A swing trader monitoring the S&amp;P 500 index (^GSPC) uses the Intraday 5-Minute Price Data API to track price movements over the course of the trading day. By analyzing the 5-minute intervals, they can time their trades more accurately, reacting quickly to short-term market changes and optimizing their strategy for maximum return.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/5min?symbol=^VIX`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | ^VIX |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 15:55:00",
    "open": 19.71,
    "low": 19.71,
    "high": 20.18,
    "close": 20.18,
    "volume": 0
  }
]
```

---

### 1-Hour Interval Index Price

Access 1-hour interval intraday data for stock indexes using the Intraday 1-Hour Price Data API. This API provides detailed price movements and volume within hourly intervals, making it ideal for tracking medium-term market trends during the trading day.

The FMP Intraday 1-Hour Price Data API delivers hourly price data for stock indexes, allowing analysts and traders to track market trends and price movements throughout the day. With open, high, low, and close prices for each hour, this API is suited for those monitoring medium-term intraday performance. Key features include: Hourly Interval Data: Retrieve open, high, low, and close prices for stock indexes at 1-hour intervals throughout the trading day. Track Medium-Term Movements: Perfect for traders and analysts interested in observing trends within hourly windows rather than minute-by-minute fluctuations. Volume Data: Analyze hourly trading volumes to gain insights into market activity and liquidity. Intraday Trading Support: Ideal for swing traders and medium-term strategies that require detailed data without overwhelming granularity. This API is particularly useful for traders, analysts, and portfolio managers who need to assess market behavior within hourly intervals to inform their trading decisions. Example Use Case A swing trader using the Intraday 1-Hour Price Data API monitors the S&amp;P 500 index (^GSPC) to observe price movements across several trading hours. With hourly updates, they can identify emerging trends and adjust their positions without the need to track minute-by-minute fluctuations.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1hour?symbol=^VIX`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | ^VIX |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 15:30:00",
    "open": 20.39,
    "low": 19.64,
    "high": 20.71,
    "close": 20.18,
    "volume": 0
  }
]
```

---

## Latest Constituents

### S&P 500 Index

Access detailed data on the S&P 500 index using the S&P 500 Index API. Track the performance and key information of the companies that make up this major stock market index.

The FMP S&amp;P 500 Index API provides comprehensive data on the companies listed in the S&amp;P 500, one of the most widely followed stock market indexes. This API delivers information about each constituent's name, symbol, sector, sub-sector, headquarters location, and other relevant details. It is ideal for investors, analysts, and researchers who need current and historical data on the S&amp;P 500's performance. Key features include: Company-Level Data: Access detailed information about each company in the S&amp;P 500, including their sector and sub-sector. Historical Additions: Track when companies were first added to the S&amp;P 500, giving insights into index composition changes over time. Geographic Information: Get headquarters locations for each company, offering a geographic perspective on the index. Industry and Sector Data: Analyze the distribution of companies across sectors and sub-sectors for a deeper understanding of market performance. This API is ideal for portfolio managers, financial analysts, and institutional investors who need up-to-date information on the S&amp;P 500 and its constituents. Example Use Case An asset manager is evaluating the sector allocation of their portfolio against the S&amp;P 500. By using the S&amp;P 500 Index API, they can retrieve sector and sub-sector data for each company in the index and adjust their asset allocation strategy to more closely match the index's composition.

**Endpoint:** `https://financialmodelingprep.com/stable/sp500-constituent`

**Example Response**

```json
[
  {
    "symbol": "FDXF",
    "name": "FedEx Freight Holding Company, Inc.",
    "sector": "Industrials",
    "subSector": "Integrated Freight & Logistics",
    "headQuarter": "Harrison, Arkansas",
    "dateFirstAdded": "2026-06-01",
    "cik": "0002082247",
    "founded": "1971-01-01"
  }
]
```

---

### Nasdaq Index

Access comprehensive data for the Nasdaq index with the Nasdaq Index API. Monitor real-time movements and track the historical performance of companies listed on this prominent stock exchange.

The FMP Nasdaq Index API provides up-to-date information on companies listed on the Nasdaq stock exchange. This API offers key details about each constituent, such as company name, symbol, sector, sub-sector, headquarters, and founding date. Whether you're tracking real-time movements or conducting historical analysis, this API is essential for those who need data on one of the world&rsquo;s largest stock exchanges. Key features include: Company Information: Access detailed data for Nasdaq-listed companies, including industry classification and headquarters location. Real-Time Monitoring: Track current and up-to-date information on Nasdaq constituents. Historical Insights: Analyze data about companies' founding dates and industry segments to understand long-term trends. Sector and Sub-Sector Breakdown: Evaluate the distribution of companies across various industries and sectors. This API is a valuable resource for traders, portfolio managers, and analysts who need real-time insights and historical data on Nasdaq-listed companies. Example Use Case A financial analyst monitoring the technology sector uses the Nasdaq Index API to track the real-time performance of Nasdaq-listed companies, such as Apple Inc. (AAPL). By retrieving sector-specific data, the analyst can make informed decisions on market trends and identify potential investment opportunities in the tech industry.

**Endpoint:** `https://financialmodelingprep.com/stable/nasdaq-constituent`

**Example Response**

```json
[
  {
    "symbol": "ADBE",
    "name": "Adobe Inc.",
    "sector": "Technology",
    "subSector": "Software - Infrastructure",
    "headQuarter": "San Jose, CA",
    "dateFirstAdded": null,
    "cik": "0000796343",
    "founded": "1982-12-01"
  }
]
```

---

### Dow Jones

Access data on the Dow Jones Industrial Average using the Dow Jones API. Track current values, analyze trends, and get detailed information about the companies that make up this important stock index.

The FMP Dow Jones Industrial Average API provides comprehensive information on the companies that are part of this iconic index. This API offers key details such as company name, symbol, sector, sub-sector, headquarters, and founding date, helping investors and analysts monitor the performance of one of the most widely followed stock market indexes. Key features include: Detailed Company Information: Access key details about Dow Jones constituents, including sector, sub-sector, and geographic location. Track Real-Time Trends: Follow current movements and trends in the Dow Jones Industrial Average. Sector Breakdown: Analyze how the index is divided across different sectors and sub-sectors for deeper insights. Historical Additions: See when companies were first added to the Dow Jones, providing context on index changes. This API is ideal for financial professionals, portfolio managers, and analysts who need accurate and up-to-date information on the Dow Jones Industrial Average. Example Use Case A portfolio manager tracking the Dow Jones Industrial Average uses the Dow Jones API to access detailed data on newly added companies, like Amazon (AMZN). By analyzing the sector and sub-sector breakdown, the manager can evaluate the impact of changes in the index on their investment strategy.

**Endpoint:** `https://financialmodelingprep.com/stable/dowjones-constituent`

**Example Response**

```json
[
  {
    "symbol": "NVDA",
    "name": "Nvidia",
    "sector": "Technology",
    "subSector": "Semiconductors",
    "headQuarter": "Santa Clara, CA",
    "dateFirstAdded": "2024-11-08",
    "cik": "0001045810",
    "founded": "1993-04-05"
  }
]
```

---

## Historical Constituents

### Historical S&P 500

Retrieve historical data for the S&P 500 index using the Historical S&P 500 API. Analyze past changes in the index, including additions and removals of companies, to understand trends and performance over time.

The FMP Historical S&amp;P 500 API provides comprehensive historical data on changes to the S&amp;P 500 index. This includes information on when companies were added or removed, along with the reasons behind these changes. It is an essential tool for analysts, portfolio managers, and researchers who need to track historical performance and trends within this key stock index. Key features include: Additions &amp; Removals: Access historical records of companies added to or removed from the S&amp;P 500, including relevant dates and reasons for the changes. Market Capitalization Changes: Track changes in the index composition driven by shifts in market capitalization. Historical Index Insights: Analyze how the composition of the S&amp;P 500 has evolved over time and how these changes impact market performance. Company-Specific Data: Retrieve details about each company that has been added or removed, including symbols and company names. This API is particularly useful for financial analysts, researchers, and portfolio managers who want to analyze how changes in the S&amp;P 500 index affect long-term market trends. Example Use Case A financial researcher uses the Historical S&amp;P 500 API to study how the composition of the index has changed over the last decade. By analyzing additions and removals, such as the recent inclusion of Dell Technologies (DELL) in place of Etsy (ETSY), they can assess how shifts in market capitalization and industry representation affect overall index performance.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-sp500-constituent`

**Example Response**

```json
[
  {
    "dateAdded": "June 01, 2026",
    "addedSecurity": "FedEx Freight Holding Company, Inc.",
    "removedTicker": "EPAM",
    "removedSecurity": "EPAM Systems, Inc.",
    "date": "2026-06-01",
    "symbol": "FDXF",
    "reason": "Market capitalization change."
  }
]
```

---

### Historical Nasdaq

Access historical data for the Nasdaq index using the Historical Nasdaq API. Analyze changes in the index composition and view how it has evolved over time, including company additions and removals.

The FMP Historical Nasdaq API provides detailed historical records of changes to the Nasdaq index. This includes data on when companies were added or removed, along with reasons for these changes, such as re-rankings or market capitalization adjustments. It&rsquo;s an essential tool for analysts and investors who want to track the Nasdaq&rsquo;s historical performance and composition. Key features include: Company Additions &amp; Removals: Access historical data on which companies have been added or removed from the Nasdaq, including relevant dates. Reasons for Changes: Understand why changes occurred in the index, such as re-rankings or shifts in market capitalization. Historical Analysis: Analyze the evolution of the Nasdaq index composition over time and how it has impacted overall market performance. Detailed Company Data: Retrieve information on specific companies added to or removed from the Nasdaq, including their symbol, name, and sector. This API is particularly useful for investors, analysts, and researchers who need to study historical trends and changes in the Nasdaq index. Example Use Case A market analyst uses the Historical Nasdaq API to study changes in the composition of the Nasdaq index over the last five years. By examining data like the inclusion of Arm Holdings (ARM) and the removal of Sirius XM (SIRI) in 2024, they can assess how industry shifts and market dynamics have influenced the index&rsquo;s overall performance.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-nasdaq-constituent`

**Example Response**

```json
[
  {
    "dateAdded": "January 20, 2026",
    "addedSecurity": "Walmart",
    "removedTicker": "AZN",
    "removedSecurity": "AstraZeneca",
    "date": "2026-01-19",
    "symbol": "WMT",
    "reason": "Walmart transferred its listing from NYSE to NASDAQ and replaced AstraZeneca in the index"
  }
]
```

---

### Historical Dow Jones

Access historical data for the Dow Jones Industrial Average using the Historical Dow Jones API. Analyze changes in the index’s composition and study its performance across different periods.

The FMP Historical Dow Jones API offers detailed records of changes to the Dow Jones Industrial Average, one of the most widely recognized stock indexes in the world. This API allows users to access information on companies added or removed from the index, along with reasons for those changes. It&rsquo;s an invaluable tool for anyone conducting historical analysis of this major market indicator. Key features include: Company Additions &amp; Removals: Access detailed data on which companies were added or removed from the Dow Jones index, including relevant dates. Reasons for Changes: Understand why companies were added or removed, such as market capitalization shifts or industry reclassifications. Historical Composition: Analyze how the makeup of the Dow Jones has changed over time and how these changes have impacted the overall index. Detailed Company Data: Retrieve information on specific companies, including their symbols, names, and the date they were added or removed from the index. This API is ideal for investors, market analysts, and researchers who want to explore historical changes in the Dow Jones and understand the factors driving those changes. Example Use Case A market researcher uses the Historical Dow Jones API to study how the index has evolved over the past decade. By examining changes like the inclusion of Amazon (AMZN) and the removal of Walgreens Boots Alliance (WBA) in 2024, the researcher can better understand how shifts in market capitalization and industry performance have influenced the Dow Jones over time.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-dowjones-constituent`

**Example Response**

```json
[
  {
    "dateAdded": "November 8, 2024",
    "addedSecurity": "Nvidia",
    "removedTicker": "INTC",
    "removedSecurity": "Intel Corporation",
    "date": "2024-11-07",
    "symbol": "NVDA",
    "reason": "Market capitalization change"
  }
]
```

---

# Commodity

## Commodities

### Commodities List

Access an extensive list of tracked commodities across various sectors, including energy, metals, and agricultural products. The FMP Commodities List API provides essential data on tradable commodities, giving investors the ability to explore market options.

The FMP Commodities List API offers users the ability to access a detailed list of tradable commodities. Whether you&rsquo;re tracking energy futures, precious metals, or agricultural products, this API provides comprehensive data, including symbols, trade months, and associated currencies. Key features include: Wide Commodity Coverage: View all available commodities across sectors such as energy (oil, natural gas), metals (gold, silver), and agriculture (corn, wheat). This diverse coverage makes it easier to find and analyze various markets. Market Insights: With trade month and currency data provided, investors and analysts can better understand global market trends and pricing structures within the commodities sector. Data: Stay updated with the most current information on commodities, allowing for timely and informed investment decisions. For instance, users can access information on the "30 Day Fed Fund Futures" commodity, seeing details like its symbol, trade month, and associated currency, helping to track specific commodities for trading and hedging purposes.

**Endpoint:** `https://financialmodelingprep.com/stable/commodities-list`

**Example Response**

```json
[
  {
    "symbol": "ESUSD",
    "name": "E-Mini S&P 500",
    "exchange": null,
    "tradeMonth": "Jun",
    "currency": "USD"
  }
]
```

---

## Quotes

### Commodities Quote

Access price quotes for all commodities traded worldwide with the FMP Global Commodities API. Track market movements and identify investment opportunities with comprehensive price data.

The FMP Global Commodities API provides a complete list of price quotes for all commodities traded on exchanges around the world. This API is an essential tool for investors and traders who want to: Commodity Prices: Access commodity price quotes, including current prices, highs, lows, and opening prices. Track Market Movements: Follow the fluctuations in commodity prices over time to spot trends and make informed decisions. Identify Investment Opportunities: Use detailed commodity price data to uncover potential investment opportunities in global markets. This Commodities API provides a global view of prices, enabling users to stay informed about market conditions and make data-driven investment decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/quote?symbol=GCUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | GCUSD |

**Example Response**

```json
[
  {
    "symbol": "GCUSD",
    "name": "Gold Futures",
    "price": 4137.8,
    "changePercentage": -0.18815,
    "change": -7.8,
    "volume": 291961,
    "dayLow": 4055.7,
    "dayHigh": 4159,
    "yearHigh": 4358,
    "yearLow": 2554.2,
    "marketCap": null,
    "priceAvg50": 3750.438,
    "priceAvg200": 3303.4436,
    "exchange": "COMMODITY",
    "open": 4144,
    "previousClose": 4145.6,
    "timestamp": 1761339599
  }
]
```

---

### Commodities Quote Short

Get fast and accurate quotes for commodities with the FMP Commodities Quick Quote API. Instantly access the current price, recent changes, and trading volume for various commodities.

The FMP Commodities Quick Quote API provides a concise and efficient way to retrieve key information on commodities. Whether you&rsquo;re looking for the latest price, recent market changes, or trading volume, this API delivers the essential data you need for quick analysis and decision-making. Instant Price Updates: Receive price data for various commodities, ensuring you're always up to date with the market. Market Change Tracking: Stay informed about price changes, allowing for fast reactions to market movements. Volume Insights: Access the latest trading volume data to gauge market activity and liquidity. This API is ideal for investors, traders, and financial analysts who need quick access to essential market data without the complexity of in-depth reports. Example: For instance, you can use this API to instantly retrieve the current price of gold (symbol: GCUSD), see the price change (-7.2), and track the trading volume (69,930), providing a snapshot of the market&rsquo;s performance at a glance.

**Endpoint:** `https://financialmodelingprep.com/stable/quote-short?symbol=GCUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | GCUSD |

**Example Response**

```json
[
  {
    "symbol": "GCUSD",
    "price": 4137.8,
    "change": -7.8,
    "volume": 291961
  }
]
```

---

### All Commodities Quotes

Access quotes for multiple commodities at once with the FMP Batch Commodities Quotes API. Instantly track price changes, volume, and other key metrics for a broad range of commodities.

The FMP Batch Commodities Quotes API allows users to retrieve live price data for a wide selection of commodities in one request. This API is designed for investors, traders, and analysts who need to monitor several commodities simultaneously and make quick, informed decisions based on market information. Batch Quotes: Retrieve quotes for multiple commodities in a single API call, simplifying the process of tracking a wide range of assets. Updates: Get up-to-the-minute pricing, ensuring you&rsquo;re always working with the most current market data. Market Metrics: Access additional metrics such as price changes and trading volume to provide context to market movements. This API is essential for professionals who need efficient access to commodity prices without having to query each asset individually. You can use this API to simultaneously retrieve the latest price for commodities such as DCUSD (current price: $22.29, change: -0.2, volume: 284), allowing for fast analysis and comparison of market data.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-commodity-quotes`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| short | boolean | true |

**Example Response**

```json
[
  {
    "symbol": "DCUSD",
    "price": 17.85,
    "change": 0.42,
    "volume": 158
  }
]
```

---

## End Of Day

### Light Chart

Access historical end-of-day prices for various commodities with the FMP Historical Commodities Price API. Analyze past price movements, trading volume, and trends to support informed decision-making.

The FMP Historical Commodities Price API offers users access to end-of-day pricing data for a wide range of commodities. This API is designed for investors, traders, and analysts who need to perform historical analysis on commodities markets, track price trends, and make informed predictions based on past data. End-of-Day Pricing: Retrieve accurate historical prices for commodities, including key metrics like trading volume, to analyze market performance over time. Comprehensive Historical Data: Access a detailed record of price changes for commodities over any chosen period. Trading Volume Insights: Evaluate the trading activity for each commodity with volume data included alongside price information. This API is ideal for financial professionals looking to analyze historical commodity data for research, risk management, or strategic trading purposes.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/light?symbol=GCUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | GCUSD |
| from | date | 2026-01-27 |
| to | date | 2026-04-27 |

**Example Response**

```json
[
  {
    "symbol": "GCUSD",
    "date": "2026-06-05",
    "price": 4365.3,
    "volume": 173833
  }
]
```

---

### Full Chart

Access full historical end-of-day price data for commodities with the FMP Comprehensive Commodities Price API. This API enables users to analyze long-term price trends, patterns, and market movements in great detail.

The FMP Comprehensive Commodities Price API provides detailed historical data for various commodities, including opening, high, low, and closing prices, as well as trading volume and price changes. This API is designed for investors, analysts, and traders who need in-depth market insights to evaluate the performance of commodities over time and make data-driven decisions. Detailed Historical Data: Access historical end-of-day data, including opening, closing, high, and low prices, trading volume, and price changes. Trend Analysis: Analyze long-term price trends and market patterns to better understand the volatility and movement of commodities. Comprehensive View: Evaluate not only price movements but also volume and volatility to get a full picture of market conditions. This API is a powerful tool for professionals looking to assess long-term trends and patterns in commodity markets, helping to predict future price movements or develop investment strategies based on historical data.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=GCUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | GCUSD |
| from | date | 2026-01-27 |
| to | date | 2026-04-27 |

**Example Response**

```json
[
  {
    "symbol": "GCUSD",
    "date": "2026-06-05",
    "open": 4503,
    "high": 4508.7,
    "low": 4336.6,
    "close": 4365.3,
    "volume": 173833,
    "change": -137.7,
    "changePercent": -3.05796,
    "vwap": 4428.4
  }
]
```

---

## Intraday

### 1-Minute Interval Commodities Chart

Track short-term price movements for commodities with the FMP 1-Minute Interval Commodities Chart API. This API provides detailed 1-minute interval data, enabling precise monitoring of intraday market changes.

The FMP 1-Minute Interval Commodities Chart API delivers minute-by-minute price data for commodities, including open, high, low, and close prices, as well as trading volume. This API is ideal for day traders, analysts, and market participants who require highly granular data to monitor price fluctuations and respond to market trends with speed and accuracy. Intraday Data: Access up-to-the-minute price data for commodities, making it easier to track short-term price movements. Detailed Price Information: View open, high, low, and close prices, along with trading volume, for precise analysis of market trends. Fast Decision-Making: The 1-minute interval data supports fast decision-making for intraday trading, allowing users to act on market opportunities as they arise. This API is a valuable resource for active traders and investors who need to stay on top of price changes in the fast-moving commodities market.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1min?symbol=GCUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | GCUSD |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 16:59:00",
    "open": 4352.6,
    "low": 4352.6,
    "high": 4354.6,
    "close": 4353.9,
    "volume": 71
  }
]
```

---

### 5-Minute Interval Commodities Chart

Monitor short-term price movements with the FMP 5-Minute Interval Commodities Chart API. This API provides detailed 5-minute interval data, enabling users to track near-term price trends for more strategic trading and investment decisions.

The FMP 5-Minute Interval Commodities Chart API delivers price data at 5-minute intervals, offering a balance between granularity and broader trend analysis. It includes open, high, low, and close prices, as well as trading volume for commodities. This API is ideal for traders and investors who want to track short-term market activity but prefer a slightly broader view than 1-minute data can provide. Short-Term Trend Analysis: Access 5-minute interval data to monitor price movements and identify short-term trends in commodity markets. Detailed Pricing Information: Retrieve detailed price data for each 5-minute interval, including open, high, low, and close prices, along with volume. Strategic Trading: Use the 5-minute interval data to spot patterns and price movements, helping traders refine their strategies and make more informed decisions. This API is perfect for traders looking to balance trading needs with a slightly longer-term perspective on commodity market movements.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/5min?symbol=GCUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | GCUSD |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 16:55:00",
    "open": 4352.5,
    "low": 4352.5,
    "high": 4355.8,
    "close": 4353.9,
    "volume": 293
  }
]
```

---

### 1-Hour Interval Commodities Chart

Monitor hourly price movements and trends with the FMP 1-Hour Interval Commodities Chart API. This API provides hourly data, offering a detailed look at price fluctuations throughout the trading day to support mid-term trading strategies and market analysis.

The FMP 1-Hour Interval Commodities Chart API provides access to 1-hour interval pricing data for commodities, including open, high, low, and close prices, along with trading volume. This data is ideal for traders and analysts who need to track hourly trends, offering a balance between short-term and daily price analysis. By focusing on hourly intervals, users can capture significant intraday movements while avoiding the noise of minute-level fluctuations. Hourly Trend Monitoring: Track price movements and trends for commodities with hourly updates, providing a clearer picture of market direction throughout the day. Detailed Pricing Information: Retrieve open, high, low, and close prices for each hour, along with trading volume, to understand market activity during specific time frames. Mid-Term Strategy Support: Use the hourly data to spot intraday trends, helping traders make more informed decisions and refine mid-term strategies. This API is a valuable tool for traders, investors, and analysts looking to monitor price trends over the course of the trading day, providing actionable insights for strategic trades.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1hour?symbol=GCUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | GCUSD |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 16:00:00",
    "open": 4343.7,
    "low": 4336.6,
    "high": 4355.8,
    "close": 4353.9,
    "volume": 4141
  }
]
```

---

# Crypto

## Cryptocurrency

### Cryptocurrency List

Access a comprehensive list of all cryptocurrencies traded on exchanges worldwide with the FMP Cryptocurrencies Overview API. Get detailed information on each cryptocurrency to inform your investment strategies.

The FMP Cryptocurrencies Overview API provides detailed information on all cryptocurrencies that are actively traded on global exchanges. This API is essential for: Cryptocurrency Identification: Access a list of all traded cryptocurrencies, including their symbols, names, and the fiat currency they are paired with. This data helps investors identify different cryptocurrencies and understand their market presence. Exchange Details: The API also provides information about the exchange where the cryptocurrency is listed, including the exchange name and a short name identifier. This allows investors to track where each cryptocurrency is traded. Informed Decision-Making: Use the detailed data provided by this API to track cryptocurrency performance, monitor market trends, and make informed investment decisions. Example Market Analysis: A crypto trader might use the Cryptocurrencies Overview API to compile a list of all cryptocurrencies paired with USD across different exchanges. By analyzing this data, the trader can identify which cryptocurrencies are gaining popularity and may present investment opportunities.

**Endpoint:** `https://financialmodelingprep.com/stable/cryptocurrency-list`

**Example Response**

```json
[
  {
    "symbol": "MIOTAUSD",
    "name": "IOTA USD",
    "exchange": "CCC",
    "icoDate": "2017-11-09",
    "circulatingSupply": 4232705124,
    "totalSupply": 4788606639
  }
]
```

---

## Quotes

### Full Cryptocurrency Quote

Access real-time quotes for all cryptocurrencies with the FMP Full Cryptocurrency Quote API. Obtain comprehensive price data including current, high, low, and open prices.

The Full Cryptocurrency Quote API provides real-time quotes for all cryptocurrencies traded on exchanges worldwide. This endpoint offers detailed information such as: Current Price: Get the latest price of any cryptocurrency. High, Low, and Open Prices: Access the highest, lowest, and opening prices for the day. Investors can use the Full Cryptocurrency Quote API to: Monitor Real-Time Prices: Stay updated with real-time prices of all cryptocurrencies traded globally. Track Price Movements: Follow the movement of cryptocurrency prices over time to identify trends and patterns. Identify Investment Opportunities: Use comprehensive price data to spot potential investment opportunities. Make Informed Trading Decisions: Base your trading decisions on up-to-date and accurate cryptocurrency price data.

**Endpoint:** `https://financialmodelingprep.com/stable/quote?symbol=BTCUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | BTCUSD |

**Example Response**

```json
[
  {
    "symbol": "BTCUSD",
    "name": "Bitcoin USD",
    "price": 111416.49,
    "changePercentage": 0.33705,
    "change": 374.27,
    "volume": 656809741,
    "dayLow": 110715.73,
    "dayHigh": 111929.37,
    "yearHigh": 126198.07,
    "yearLow": 66360.59,
    "marketCap": 2200058868410,
    "priceAvg50": 114156.7,
    "priceAvg200": 108462.445,
    "exchange": "CRYPTO",
    "open": 111042.22,
    "previousClose": 111042.22,
    "timestamp": 1761407984
  }
]
```

---

### Cryptocurrency Quote Short

Access real-time cryptocurrency quotes with the FMP Cryptocurrency Quick Quote API. Get a concise overview of current crypto prices, changes, and trading volume for a wide range of digital assets.

The FMP Cryptocurrency Quick Quote API provides users with immediate access to essential cryptocurrency price data. It&rsquo;s designed for traders, investors, and analysts who need up-to-the-minute information on the crypto market, including: Real-Time Crypto Prices: Retrieve the latest prices for popular cryptocurrencies like Bitcoin, Ethereum, and more. Market Changes: View real-time price changes to stay informed of market fluctuations. Trading Volume: Access data on trading volumes to assess market activity and liquidity for specific cryptocurrencies. This API offers a quick and effective way to monitor cryptocurrency prices and make informed decisions based on real-time market data. Example Use Case A day trader can use the Cryptocurrency Quick Quote API to track the price of Bitcoin and monitor real-time changes in price and volume, helping them make quick trading decisions in volatile markets.

**Endpoint:** `https://financialmodelingprep.com/stable/quote-short?symbol=BTCUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | BTCUSD |

**Example Response**

```json
[
  {
    "symbol": "BTCUSD",
    "price": 111416.49,
    "change": 374.27,
    "volume": 656809741
  }
]
```

---

### All Cryptocurrencies Quotes

Access live price data for a wide range of cryptocurrencies with the FMP Real-Time Cryptocurrency Batch Quotes API. Get real-time updates on prices, market changes, and trading volumes for digital assets in a single request.

The FMP Real-Time Cryptocurrency Batch Quotes API is designed for investors, traders, and financial analysts who need to track multiple cryptocurrency prices simultaneously. This API provides: Real-Time Cryptocurrency Prices: Retrieve current prices for a broad range of digital assets in a single batch request. Market Movement Tracking: Keep up with price changes to stay ahead of trends in the fast-paced crypto market. Volume Data: Access trading volume information to gauge liquidity and market activity. This API is ideal for users who need quick, real-time access to prices and trading volumes for a variety of cryptocurrencies in one convenient response. Example Use Case A portfolio manager can use the Real-Time Cryptocurrency Batch Quotes API to monitor the prices and market activity of multiple cryptocurrencies in real-time, allowing them to make quick and informed decisions across their digital asset portfolio.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-crypto-quotes`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| short | boolean | true |

**Example Response**

```json
[
  {
    "symbol": "00USD",
    "price": 0.00991214,
    "change": 0.0001174555,
    "volume": 68545
  }
]
```

---

## End Of Day

### Historical Cryptocurrency Light Chart

Access historical end-of-day prices for a variety of cryptocurrencies with the Historical Cryptocurrency Price Snapshot API. Track trends in price and trading volume over time to better understand market behavior.

The Historical Cryptocurrency Price Snapshot API provides crucial insights into the performance of cryptocurrencies over time by offering: End-of-Day Prices: Retrieve historical end-of-day prices for cryptocurrencies, allowing you to analyze long-term market trends and patterns. Trading Volume Data: Access volume data to evaluate market activity during specific time frames. Price Trend Analysis: Use this data to review how a cryptocurrency's value has changed, assisting in making informed investment decisions. This API is essential for traders, analysts, and investors looking to perform technical analysis or monitor how the market has evolved over time. Example Use Case An analyst can use the Historical Cryptocurrency Price Snapshot API to backtest trading strategies by reviewing past price movements and identifying patterns that could influence future price action.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/light?symbol=BTCUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | BTCUSD |
| from | date | 2026-01-27 |
| to | date | 2026-04-27 |

**Example Response**

```json
[
  {
    "symbol": "BTCUSD",
    "date": "2026-06-06",
    "price": 60538.92,
    "volume": 41787585310
  }
]
```

---

### Historical Cryptocurrency Full Chart

Access comprehensive end-of-day (EOD) price data for cryptocurrencies with the Full Historical Cryptocurrency Data API. Analyze long-term price trends, market movements, and trading volumes to inform strategic decisions.

The Full Historical Cryptocurrency Data API provides extensive historical data, including: End-of-Day (EOD) Prices: Retrieve daily open, high, low, close (OHLC) price data for cryptocurrencies. Comprehensive Market Data: Access trading volumes, price changes, and VWAP (Volume Weighted Average Price) to gain insights into market behavior. Analyze Long-Term Trends: Review historical price data to track long-term trends, volatility, and market cycles, enabling better decision-making for investors and analysts. This API is essential for long-term investors, analysts, and institutions seeking to evaluate market movements, identify trends, and support strategic planning. Example Use Case A long-term cryptocurrency investor could use the Full Historical Cryptocurrency Data API to analyze Bitcoin&rsquo;s market performance over the past year, identifying key resistance levels and potential buying opportunities based on historical price trends.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=BTCUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | BTCUSD |
| from | date | 2026-01-27 |
| to | date | 2026-04-27 |

**Example Response**

```json
[
  {
    "symbol": "BTCUSD",
    "date": "2026-06-06",
    "open": 60761.37109,
    "high": 61876,
    "low": 59228,
    "close": 60538.92,
    "volume": 41787585310,
    "change": -222.45,
    "changePercent": -0.36610611,
    "vwap": 60547.64
  }
]
```

---

## Intraday

### 1-Minute Interval Cryptocurrency Data

Get real-time, 1-minute interval price data for cryptocurrencies with the 1-Minute Cryptocurrency Intraday Data API. Monitor short-term price fluctuations and trading volume to stay updated on market movements.

The 1-Minute Cryptocurrency Intraday Data API offers precise, real-time updates on cryptocurrency price movements, including: 1-Minute Price Intervals: Retrieve data on cryptocurrency prices at 1-minute intervals, including open, high, low, close (OHLC) values. Real-Time Volume Information: Access detailed trading volume data for every minute, enabling quick insights into market activity. Track Short-Term Price Movements: Analyze short-term trends in cryptocurrency prices to capitalize on market opportunities or identify trends early. This API is vital for day traders, analysts, and algorithmic traders who need fast, actionable data to track the fast-moving cryptocurrency markets. Example Use Case A day trader can use the 1-Minute Cryptocurrency Intraday Data API to monitor real-time price movements and volume spikes, making quick decisions based on emerging market trends or breakouts.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1min?symbol=BTCUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | BTCUSD |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-06 15:40:00",
    "open": 60538.92,
    "low": 60523.99,
    "high": 60547.97,
    "close": 60547.97,
    "volume": 508022980
  }
]
```

---

### 5-Minute Interval Cryptocurrency Data

Analyze short-term price trends with the 5-Minute Interval Cryptocurrency Data API. Access real-time, intraday price data for cryptocurrencies to monitor rapid market movements and optimize trading strategies.

The 5-Minute Interval Cryptocurrency Data API provides detailed intraday data for cryptocurrencies, including: Short-Term Price Movements: Track prices in 5-minute intervals, offering granular insights into cryptocurrency performance throughout the trading day. Real-Time Market Analysis: Access real-time updates on open, high, low, and close (OHLC) prices, as well as trading volumes, to capture intraday market shifts. Support for Technical Analysis: Use 5-minute interval data to perform advanced technical analysis, such as identifying support and resistance levels, spotting short-term trends, or implementing day trading strategies. This API is essential for active traders, analysts, and investors who need to stay informed of fast-moving price changes and capitalize on short-term market fluctuations. Example Use Case A day trader uses the 5-Minute Interval Cryptocurrency Data API to track Bitcoin's price movements throughout the day. By analyzing the short-term price trends, the trader identifies optimal entry and exit points for their trades.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/5min?symbol=BTCUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | BTCUSD |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-06 15:35:00",
    "open": 60587.24,
    "low": 60500.05,
    "high": 60593.62,
    "close": 60569.12,
    "volume": 41281099407
  }
]
```

---

### 1-Hour Interval Cryptocurrency Data

Access detailed 1-hour intraday price data for cryptocurrencies with the 1-Hour Interval Cryptocurrency Data API. Track hourly price movements to gain insights into market trends and make informed trading decisions throughout the day.

The 1-Hour Interval Cryptocurrency Data API provides key hourly updates on cryptocurrency prices, offering users a granular view of market fluctuations: Hourly Price Updates: Receive cryptocurrency price data, including open, high, low, and close (OHLC) prices, as well as trading volumes, updated every hour. Comprehensive Market Monitoring: Use hourly data to monitor market trends, track price momentum, and identify potential trading opportunities. Effective for Trend Analysis: Leverage hourly intervals to observe intraday price patterns, helping you make better decisions for day trading, swing trading, or long-term analysis. This API is ideal for traders and investors who want a closer look at how prices evolve over the course of a trading day, enabling them to act swiftly in fast-paced markets. Example Use Case A swing trader uses the 1-Hour Interval Cryptocurrency Data API to monitor the price of Ethereum. By analyzing hourly trends, the trader can spot potential breakouts or pullbacks and adjust their positions accordingly.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1hour?symbol=BTCUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | BTCUSD |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-06 15:00:00",
    "open": 60598.27,
    "low": 60500.05,
    "high": 60755,
    "close": 60569.12,
    "volume": 86028364105
  }
]
```

---

# Fundraisers

## Crowdfunding

### Latest Crowdfunding Campaigns

Discover the most recent crowdfunding campaigns with the FMP Latest Crowdfunding Campaigns API. Stay informed on which companies and projects are actively raising funds, their financial details, and offering terms.

The FMP Latest Crowdfunding Campaigns API provides detailed information on current crowdfunding campaigns, including the names of issuers, offering types, and financial data. This API is essential for investors, analysts, and platforms that want to track the latest crowdfunding activity. Track Crowdfunding Campaigns: Access the most up-to-date information on crowdfunding campaigns, including company names, funding goals, and offering types. Detailed Financial Information: View key financial metrics such as total assets, cash equivalents, debt, and net income for each company running a crowdfunding campaign. Company Backgrounds: Get insights into the legal status and jurisdiction of the companies, including the number of employees and other relevant organizational data. This API is a valuable tool for those looking to follow new crowdfunding opportunities, assess potential investments, or stay up to date on market trends in the crowdfunding space. Example Use Case An investor can use the Crowdfunding Campaigns API to review the financial health and offering details of various crowdfunding campaigns, helping them evaluate potential opportunities and diversify their portfolio.

**Endpoint:** `https://financialmodelingprep.com/stable/crowdfunding-offerings-latest?page=0&limit=100`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| page | number | 0 |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "cik": "0002075154",
    "companyName": "Kaylaan LLC",
    "date": "01-01-1983",
    "filingDate": "2026-06-05 00:00:00",
    "acceptedDate": "2026-06-05 16:05:17",
    "formType": "C/A",
    "formSignification": "Offering Statement Amendement",
    "nameOfIssuer": "Kaylaan LLC",
    "legalStatusForm": "Limited Liability Company",
    "jurisdictionOrganization": "NY",
    "issuerStreet": "329 JERICHO TURNPIKE, SUITE G2",
    "issuerCity": "FLORAL PARK",
    "issuerStateOrCountry": "NY",
    "issuerZipCode": "11001",
    "issuerWebsite": "https://www.kaylaan.com/",
    "intermediaryCompanyName": "Honeycomb Portal LLC",
    "intermediaryCommissionCik": "0001705726",
    "intermediaryCommissionFileNumber": "007-00119",
    "compensationAmount": "8.5% of the total offering amount upon a successful raise. $500 Platform Fee. 3% investment fee capped at $75. Credit Card: 5.5% + $2; Honeycomb Wallet: 0%; Hybrid (HW + ACH): 2%, capped at $30. A Loan Servicing Fee of .25% assessed monthly.",
    "financialInterest": "None",
    "securityOfferedType": "Debt",
    "securityOfferedOtherDescription": null,
    "numberOfSecurityOffered": 0,
    "offeringPrice": 1,
    "offeringAmount": 30000,
    "overSubscriptionAccepted": "Y",
    "overSubscriptionAllocationType": "First-come, first-served basis",
    "maximumOfferingAmount": 65000,
    "offeringDeadlineDate": "06-30-2026",
    "currentNumberOfEmployees": 2,
    "totalAssetMostRecentFiscalYear": 58322,
    "totalAssetPriorFiscalYear": 36321,
    "cashAndCashEquiValentMostRecentFiscalYear": 5038,
    "cashAndCashEquiValentPriorFiscalYear": 1073,
    "accountsReceivableMostRecentFiscalYear": 0,
    "accountsReceivablePriorFiscalYear": 0,
    "shortTermDebtMostRecentFiscalYear": 17968,
    "shortTermDebtPriorFiscalYear": 20691,
    "longTermDebtMostRecentFiscalYear": 94490,
    "longTermDebtPriorFiscalYear": 18951,
    "revenueMostRecentFiscalYear": 133747,
    "revenuePriorFiscalYear": 131597,
    "costGoodsSoldMostRecentFiscalYear": 52314,
    "costGoodsSoldPriorFiscalYear": 31691,
    "taxesPaidMostRecentFiscalYear": 0,
    "taxesPaidPriorFiscalYear": 0,
    "netIncomeMostRecentFiscalYear": -138317,
    "netIncomePriorFiscalYear": -5058
  }
]
```

---

### Crowdfunding Campaign Search

Search for crowdfunding campaigns by company name, campaign name, or platform with the FMP Crowdfunding Campaign Search API. Access detailed information to track and analyze crowdfunding activities.

The FMP Crowdfunding Campaign Search API allows users to search for crowdfunding campaigns based on company name, campaign name, or platform. This API is a valuable tool for investors and analysts who need to: Find Specific Campaigns: Quickly access information on specific crowdfunding campaigns, including the amount raised, number of backers, and investment deadlines. Track Company Activity: Monitor the crowdfunding activity of particular companies to identify trends or patterns over time. Identify Investment Opportunities: Use crowdfunding data to discover potential investment opportunities based on recent and ongoing campaigns. This API provides comprehensive details about crowdfunding campaigns, enabling users to make informed decisions based on up-to-date information.

**Endpoint:** `https://financialmodelingprep.com/stable/crowdfunding-offerings-search?name=enotap`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| name* | string | enotap |

**Example Response**

```json
[
  {
    "cik": "0001912939",
    "name": "Enotap LLC",
    "date": null
  }
]
```

---

### Crowdfunding By CIK

Access detailed information on all crowdfunding campaigns launched by a specific company with the FMP Crowdfunding By CIK API.

The FMP Crowdfunding By CIK API provides a comprehensive list of crowdfunding campaigns launched by companies, identified by their Central Index Key (CIK). This endpoint is invaluable for investors and analysts who need to: Identify Company-Specific Campaigns: Discover all crowdfunding campaigns initiated by companies you are interested in investing in. Track Crowdfunding Activity Over Time: Monitor the crowdfunding activity of specific companies to identify trends, growth, and changes in their fundraising efforts. Spot Investment Opportunities: Use the data on crowdfunding campaigns to uncover potential investment opportunities based on the crowdfunding strategies of companies. This API is essential for those looking to make informed decisions based on the crowdfunding activity of specific companies.

**Endpoint:** `https://financialmodelingprep.com/stable/crowdfunding-offerings?cik=0001916078`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| cik* | string | 0001916078 |

**Example Response**

```json
[
  {
    "cik": "0001916078",
    "companyName": "OYO Fitness, Inc",
    "date": "12-31-2021",
    "filingDate": "2022-07-21 00:00:00",
    "acceptedDate": "2022-07-21 17:28:54",
    "formType": "C-U",
    "formSignification": "Progress Update",
    "nameOfIssuer": "OYO Fitness, Inc",
    "legalStatusForm": "Corporation",
    "jurisdictionOrganization": "DE",
    "issuerStreet": "374 N. 750TH RD",
    "issuerCity": "OVERBROOK",
    "issuerStateOrCountry": "KS",
    "issuerZipCode": "66524",
    "issuerWebsite": "https://www.oyofitness.com/",
    "intermediaryCompanyName": "StartEngine Capital, LLC",
    "intermediaryCommissionCik": "0001665160",
    "intermediaryCommissionFileNumber": "007-00007",
    "compensationAmount": "7 - 13 percent",
    "financialInterest": "Two percent (2%) of securities of the total amount of investments raised in the offering, along the same terms as investors.",
    "securityOfferedType": "Other",
    "securityOfferedOtherDescription": "Non-Voting Common Stock",
    "numberOfSecurityOffered": 5000,
    "offeringPrice": 2,
    "offeringAmount": 10000,
    "overSubscriptionAccepted": "Y",
    "overSubscriptionAllocationType": "Other",
    "maximumOfferingAmount": 1070000,
    "offeringDeadlineDate": "07-19-2022",
    "currentNumberOfEmployees": 5,
    "totalAssetMostRecentFiscalYear": 497717,
    "totalAssetPriorFiscalYear": 248472,
    "cashAndCashEquiValentMostRecentFiscalYear": 150142,
    "cashAndCashEquiValentPriorFiscalYear": 54571,
    "accountsReceivableMostRecentFiscalYear": 0,
    "accountsReceivablePriorFiscalYear": 0,
    "shortTermDebtMostRecentFiscalYear": 3286745,
    "shortTermDebtPriorFiscalYear": 2214117,
    "longTermDebtMostRecentFiscalYear": 82243,
    "longTermDebtPriorFiscalYear": 105850,
    "revenueMostRecentFiscalYear": 4344154,
    "revenuePriorFiscalYear": 11078510,
    "costGoodsSoldMostRecentFiscalYear": 2445024,
    "costGoodsSoldPriorFiscalYear": 5737776,
    "taxesPaidMostRecentFiscalYear": 0,
    "taxesPaidPriorFiscalYear": 0,
    "netIncomeMostRecentFiscalYear": -964551,
    "netIncomePriorFiscalYear": -10860
  }
]
```

---

## Equity

### Equity Offering Updates

Stay informed about the latest equity offerings with the FMP Equity Offering Updates API. Track new shares being issued by companies and get insights into exempt offerings and amendments.

The FMP Equity Offering Updates API provides detailed information on newly issued equity securities, including company details, offering amounts, and regulatory filings. This API is a crucial tool for investors, analysts, and market researchers who need to: Monitor New Equity Issuances: Track companies issuing new shares and stay informed about recent equity offerings. Analyze Offering Details: Access important data such as filing dates, form types, industry classifications, and the minimum investment required. Stay Compliant: Get information on exempt offerings under regulations like 06b, 3C, and 3C.1 to assess the legal status of an equity issue. This API is invaluable for keeping up-to-date with the latest equity issuances, ensuring you never miss an important offering or amendment. Example Use Case An institutional investor could use the Equity Offering Updates API to identify new investment opportunities by tracking newly issued equity offerings from companies across various sectors.

**Endpoint:** `https://financialmodelingprep.com/stable/fundraising-latest?page=0&limit=10`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| page | number | 0 |
| limit | number | 10 |
| cik | string | 0002013736 |

**Example Response**

```json
[
  {
    "cik": "0002138874",
    "companyName": "VIDOR-TX PROPERTY, LLC",
    "date": "2026-06-05",
    "filingDate": "2026-06-05 00:00:00",
    "acceptedDate": "2026-06-05 17:30:42",
    "formType": "D",
    "formSignification": "Notice of Exempt Offering of Securities",
    "entityName": "VIDOR-TX PROPERTY, LLC",
    "issuerStreet": "C/O NIGRO KARLIN SEGAL & FELDSTEIN, LLP",
    "issuerCity": "LOS ANGELES",
    "issuerStateOrCountry": "CA",
    "issuerStateOrCountryDescription": "CALIFORNIA",
    "issuerZipCode": "90025",
    "issuerPhoneNumber": "3105862432",
    "jurisdictionOfIncorporation": "DELAWARE",
    "entityType": "Limited Liability Company",
    "incorporatedWithinFiveYears": true,
    "yearOfIncorporation": "2026",
    "relatedPersonFirstName": "TODD",
    "relatedPersonLastName": "OKUM",
    "relatedPersonStreet": "C/O NIGRO KARLIN SEGAL & FELDSTEIN, LLP",
    "relatedPersonCity": "LOS ANGELES",
    "relatedPersonStateOrCountry": "CA",
    "relatedPersonStateOrCountryDescription": "CALIFORNIA",
    "relatedPersonZipCode": "90024",
    "relatedPersonRelationship": "Executive Officer",
    "industryGroupType": "Other Real Estate",
    "revenueRange": "Decline to Disclose",
    "federalExemptionsExclusions": "06b",
    "isAmendment": false,
    "dateOfFirstSale": "2026-06-01",
    "durationOfOfferingIsMoreThanYear": false,
    "securitiesOfferedAreOfEquityType": true,
    "isBusinessCombinationTransaction": false,
    "minimumInvestmentAccepted": 25000,
    "totalOfferingAmount": 2750000,
    "totalAmountSold": 2750000,
    "totalAmountRemaining": 0,
    "hasNonAccreditedInvestors": false,
    "totalNumberAlreadyInvested": 25,
    "salesCommissions": 0,
    "findersFees": 0,
    "grossProceedsUsed": 150000
  }
]
```

---

### Equity Offering Search

Easily search for equity offerings by company name or stock symbol with the FMP Equity Offering Search API. Access detailed information about recent share issuances to stay informed on company fundraising activities.

The FMP Equity Offering Search API allows users to quickly find relevant equity offering data, including details on recent share issuances and filing dates. This API is essential for investors, analysts, and compliance officers who want to: Track Company Equity Offerings: Search by company name or ticker symbol to find recent equity offerings. Analyze Issuance Data: Access key information such as offering dates, company names, and CIK (Central Index Key) numbers to get a comprehensive view of recent share issuances. Stay Informed About Market Activity: Use the API to monitor fundraising activities, assess the impact of equity offerings, and make informed investment decisions. This API provides an efficient way to stay on top of market events by offering a quick search for new equity issuances from companies across various sectors. Example Use Case An investor can use the Equity Offering Search API to identify which companies are issuing new shares, allowing them to assess the impact of equity offerings on their portfolio or potential investments.

**Endpoint:** `https://financialmodelingprep.com/stable/fundraising-search?name=NJOY`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| name* | string | NJOY |

**Example Response**

```json
[
  {
    "cik": "0001547416",
    "name": "NJOY INC",
    "date": "2014-02-28 16:00:25"
  }
]
```

---

### Equity Offering By CIK

Access detailed information on equity offerings announced by specific companies with the FMP Company Equity Offerings by CIK API. Track offering activity and identify potential investment opportunities.

The FMP Company Equity Offerings by CIK API provides a comprehensive list of all equity offerings announced by a particular company, identified by its Central Index Key (CIK). This API is essential for: Identifying Company-Specific Offerings: Quickly find and track equity offerings announced by companies you are interested in by searching with their CIK. Tracking Offering Activity Over Time: Monitor the equity offering history of specific companies to gain insights into their financing activities and strategic moves. Spotting Investment Opportunities: Use equity offering data to identify potential investment opportunities, understanding how a company&rsquo;s offering activity might impact its stock price and market position. Investors can leverage this API to stay informed about the equity offering activities of the companies they follow, allowing for more informed investment decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/fundraising?cik=0001547416`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| cik* | string | 0001547416 |

**Example Response**

```json
[
  {
    "cik": "0001547416",
    "companyName": "NJOY INC",
    "date": "2014-02-28",
    "filingDate": "2014-02-28 00:00:00",
    "acceptedDate": "2014-02-28 16:00:25",
    "formType": "D",
    "formSignification": "Notice of Exempt Offering of Securities",
    "entityName": "NJOY INC",
    "issuerStreet": "15211 N. KIERLAND BLVD., SUITE 200",
    "issuerCity": "SCOTTSDALE",
    "issuerStateOrCountry": "AZ",
    "issuerStateOrCountryDescription": "ARIZONA",
    "issuerZipCode": "85254",
    "issuerPhoneNumber": "480-397-2300",
    "jurisdictionOfIncorporation": "DELAWARE",
    "entityType": "Corporation",
    "incorporatedWithinFiveYears": null,
    "yearOfIncorporation": "",
    "relatedPersonFirstName": "CRAIG",
    "relatedPersonLastName": "WEISS",
    "relatedPersonStreet": "c/o NJOY, INC.",
    "relatedPersonCity": "SCOTTSDALE",
    "relatedPersonStateOrCountry": "AZ",
    "relatedPersonStateOrCountryDescription": "ARIZONA",
    "relatedPersonZipCode": "85254",
    "relatedPersonRelationship": "Executive Officer, Director",
    "industryGroupType": "Other",
    "revenueRange": "Decline to Disclose",
    "federalExemptionsExclusions": "06b",
    "isAmendment": false,
    "dateOfFirstSale": "2014-02-14",
    "durationOfOfferingIsMoreThanYear": false,
    "securitiesOfferedAreOfEquityType": true,
    "isBusinessCombinationTransaction": false,
    "minimumInvestmentAccepted": 0,
    "totalOfferingAmount": 71999990,
    "totalAmountSold": 71999990,
    "totalAmountRemaining": 0,
    "hasNonAccreditedInvestors": false,
    "totalNumberAlreadyInvested": 24,
    "salesCommissions": 0,
    "findersFees": 0,
    "grossProceedsUsed": 0
  }
]
```

---

# Forex

## Forex

### Forex Currency Pairs

Access a comprehensive list of all currency pairs traded on the forex market with the FMP Forex Currency Pairs API. Analyze and track the performance of currency pairs to make informed investment decisions.

The FMP Forex Currency Pairs API provides detailed information on all currency pairs traded on the global forex market. This API is essential for: Currency Pair Identification: Easily identify the various currency pairs available for trading in the forex market. A currency pair consists of a base currency and a counter currency, with the value of the pair representing how much of the counter currency is needed to purchase one unit of the base currency. Performance Tracking: Use the API to track the performance of different currency pairs over time. This data is crucial for investors and traders looking to monitor market trends and exchange rate movements. Informed Decision-Making: Leverage the comprehensive data provided by the Forex Currency Pairs API to make well-informed decisions when trading currencies. By understanding the dynamics of currency pairs, you can develop strategies that align with market conditions. This API is a valuable tool for forex traders, investors, and analysts who need to stay updated on the latest currency pairs and market trends. Example Forex Trading Strategy: A forex trader might use the Forex Currency Pairs API to identify high-volume currency pairs such as EUR/USD or GBP/JPY. By tracking the performance of these pairs over time, the trader can develop strategies to capitalize on market movements.

**Endpoint:** `https://financialmodelingprep.com/stable/forex-list`

**Example Response**

```json
[
  {
    "symbol": "ARSMXN",
    "fromCurrency": "ARS",
    "toCurrency": "MXN",
    "fromName": "Argentine Peso",
    "toName": "Mexican Peso"
  }
]
```

---

## Quotes

### Forex Quote

Access real-time forex quotes for currency pairs with the Forex Quote API. Retrieve up-to-date information on exchange rates and price changes to help monitor market movements.

The Fx Quotes API provides live exchange rate data for various currency pairs, delivering essential insights for traders and financial analysts. Here&rsquo;s how it can help you: Live Forex Quotes: Get up-to-the-minute exchange rates and price updates for different forex pairs, such as EUR/USD. Detailed Price Information: Access key data, including the current price, day&rsquo;s high and low, year&rsquo;s high and low, and percentage changes. Monitor Market Movements: Track the opening and closing prices, as well as 50-day and 200-day moving averages, to gain a comprehensive view of market trends. This API is essential for forex traders and financial professionals who need accurate and timely currency exchange data to make informed decisions. Example Use Case A forex trader uses the Fx Quotes API to monitor the EUR/USD exchange rate throughout the day. By tracking live price changes and percentage movements, the trader can time their trades and react quickly to market fluctuations.

**Endpoint:** `https://financialmodelingprep.com/stable/quote?symbol=EURUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | EURUSD |

**Example Response**

```json
[
  {
    "symbol": "EURUSD",
    "name": "EUR/USD",
    "price": 1.16269,
    "changePercentage": 0.07590828,
    "change": 0.00088191,
    "volume": 140619,
    "dayLow": 1.16009,
    "dayHigh": 1.16503,
    "yearHigh": 1.19188,
    "yearLow": 1.01779,
    "marketCap": null,
    "priceAvg50": 1.16975,
    "priceAvg200": 1.14571,
    "exchange": "FOREX",
    "open": 1.16168,
    "previousClose": 1.16181,
    "timestamp": 1761350400
  }
]
```

---

### Forex Short Quote

Quickly access concise forex pair quotes with the Forex Quote Snapshot API. Get a fast look at live currency exchange rates, price changes, and volume in real time.

The Forex Quote Snapshot API is designed for users who need a streamlined view of forex data. It offers a quick, no-frills quote for various currency pairs, making it ideal for fast decision-making in trading environments. Real-Time Price Data: Instantly retrieve the current price for forex pairs such as EUR/USD. Brief Overview: Access essential data, including the latest price change and trading volume, in a compact format. Efficient Monitoring: Ideal for traders and analysts who need fast updates without extensive details. This API is perfect for quick checks of forex market movements, helping traders stay informed and react promptly. Example Use Case A currency trader uses the Forex Quote Snapshot API to monitor the EUR/USD pair throughout the day, quickly checking price changes and volume to make rapid trading decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/quote-short?symbol=EURUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | EURUSD |

**Example Response**

```json
[
  {
    "symbol": "EURUSD",
    "price": 1.16269,
    "change": 0.00088191,
    "volume": 140619
  }
]
```

---

### Batch Forex Quotes

Easily access real-time quotes for multiple forex pairs simultaneously with the Batch Forex Quotes API. Stay updated on global currency exchange rates and monitor price changes across different markets.

The Batch Forex Quotes API enables users to retrieve live forex quotes for numerous currency pairs in a single request, streamlining the process of monitoring multiple forex pairs at once. Track Global Exchange Rates: Get real-time prices for a wide range of currency pairs from around the world. Bulk Data Retrieval: Receive real-time forex quotes for multiple pairs, including price, change, and volume, in one request. Ideal for High-Frequency Traders: Perfect for traders and analysts who need to monitor many currency pairs quickly and efficiently. This API simplifies the process of keeping tabs on the global forex market, making it easy to track exchange rates and price fluctuations in real time. Example Use Case A forex trader uses the Batch Forex Quotes API to retrieve quotes for 50 different currency pairs at once, helping them monitor price movements and volume across global currencies in real time.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-forex-quotes`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| short | boolean | true |

**Example Response**

```json
[
  {
    "symbol": "AEDAUD",
    "price": 0.4182,
    "change": 0.0008136291,
    "volume": 0
  }
]
```

---

## End Of Day

### Historical Forex Light Chart

Access historical end-of-day forex prices with the Historical Forex Light Chart API. Track long-term price trends across different currency pairs to enhance your trading and analysis strategies.

The Historical Forex Light Chart API provides end-of-day forex prices for a wide range of currency pairs. This data is invaluable for traders and analysts looking to: Analyze Long-Term Trends: Review historical price data to identify patterns and trends that could influence future market movements. Backtest Trading Strategies: Use past data to validate trading strategies by simulating market conditions over extended timeframes. Compare Forex Pair Performance: Analyze the performance of different forex pairs over time, helping you make more informed trading decisions. This API is essential for forex traders, analysts, and investors who need access to accurate historical data for market analysis and strategy development. Example Use Case A forex trader uses the Historical Forex Light Chart API to review end-of-day prices for the EUR/USD currency pair over the past five years. By analyzing this data, the trader identifies key support and resistance levels, helping refine their trading strategy.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/light?symbol=EURUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | EURUSD |
| from | date | 2026-01-27 |
| to | date | 2026-04-27 |

**Example Response**

```json
[
  {
    "symbol": "EURUSD",
    "date": "2026-06-05",
    "price": 1.15226,
    "volume": 131392
  }
]
```

---

### Historical Forex Full Chart

Access comprehensive historical end-of-day forex price data with the Full Historical Forex Chart API. Gain detailed insights into currency pair movements, including open, high, low, close (OHLC) prices, volume, and percentage changes.

The Full Historical Forex Chart API provides extensive historical price data for a wide range of currency pairs, offering traders and analysts a deeper understanding of market trends. This data includes open, high, low, and close prices, as well as volume, VWAP (Volume Weighted Average Price), and percentage changes. This API is ideal for: Detailed Trend Analysis: Review comprehensive historical price data to analyze long-term trends and patterns in forex markets. Advanced Technical Analysis: Use OHLC data to apply technical indicators and identify potential trading signals. Strategy Backtesting: Access detailed historical data to validate and optimize trading strategies using real market conditions from past periods. This API is an essential resource for traders, analysts, and portfolio managers seeking to understand forex market movements and refine their strategies with comprehensive data. Example Use Case A portfolio manager uses the Full Historical Forex Chart API to analyze the EUR/USD pair's daily open, high, low, and close prices over the last decade. By reviewing these trends, the manager develops a more informed strategy for managing currency exposure.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=EURUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | EURUSD |
| from | date | 2026-01-27 |
| to | date | 2026-04-27 |

**Example Response**

```json
[
  {
    "symbol": "EURUSD",
    "date": "2026-06-05",
    "open": 1.16154,
    "high": 1.16445,
    "low": 1.1518,
    "close": 1.15226,
    "volume": 131392,
    "change": -0.00928,
    "changePercent": -0.79894,
    "vwap": 1.15751
  }
]
```

---

## Intraday

### 1-Minute Interval Forex Chart

Access real-time 1-minute intraday forex data with the 1-Minute Forex Interval Chart API. Track short-term price movements for precise, up-to-the-minute insights on currency pair fluctuations.

The 1-Minute Forex Interval Chart API provides high-frequency intraday data, offering a detailed view of currency pair price changes every minute. With real-time open, high, low, close (OHLC) prices and volume data, this API is ideal for: Scalping and Day Trading: Traders focused on quick entry and exit points can leverage minute-by-minute data for highly dynamic market conditions. High-Frequency Monitoring: Closely monitor short-term forex price movements to seize opportunities or manage risk during volatile market sessions. Short-Term Strategy Execution: Apply rapid trading strategies and technical analysis to capture fleeting trends and minimize risk. By using this API, traders can make timely and informed decisions in fast-moving forex markets, making it essential for high-frequency traders and those employing short-term strategies. Example Use Case A day trader uses the 1-Minute Forex Interval Chart API to track price movements in the EUR/USD currency pair. By monitoring each minute&rsquo;s open, high, low, and close prices, the trader executes a scalping strategy and optimizes profit opportunities within a single trading session.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1min?symbol=EURUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | EURUSD |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 16:59:00",
    "open": 1.15235,
    "low": 1.15226,
    "high": 1.15238,
    "close": 1.15226,
    "volume": 13
  }
]
```

---

### 5-Minute Interval Forex Chart

Track short-term forex trends with the 5-Minute Forex Interval Chart API. Access detailed 5-minute intraday data to monitor currency pair price movements and market conditions in near real-time.

The 5-Minute Forex Interval Chart API offers critical price data at 5-minute intervals, making it ideal for traders and analysts focused on short-term trends. With open, high, low, close (OHLC) prices and volume data for each 5-minute period, this API supports: Intraday Trading Strategies: Perfect for traders looking to capture price trends and make informed decisions within short timeframes. Monitoring Currency Pair Volatility: Follow price movements closely during key market sessions to capitalize on fluctuations in exchange rates. Near-Term Trend Analysis: Use this API for technical analysis and to spot patterns or breakouts that occur over 5-minute periods. This API is a valuable tool for forex traders aiming to understand and react to market conditions quickly, as well as for analysts seeking to track short-term currency pair movements. Example Use Case A forex trader monitoring the EUR/USD pair uses the 5-Minute Forex Interval Chart API to analyze price fluctuations during volatile periods. By tracking 5-minute intervals, the trader makes informed decisions on when to enter or exit trades.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/5min?symbol=EURUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | EURUSD |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 16:55:00",
    "open": 1.15224,
    "low": 1.15188,
    "high": 1.15246,
    "close": 1.15226,
    "volume": 577
  }
]
```

---

### 1-Hour Interval Forex Chart

Track forex price movements over the trading day with the 1-Hour Forex Interval Chart API. This tool provides hourly intraday data for currency pairs, giving a detailed view of trends and market shifts.

The 1-Hour Forex Interval Chart API delivers comprehensive OHLC (open, high, low, close) price and volume data for each 1-hour period. It&rsquo;s an essential tool for forex traders and analysts who need to: Monitor Intraday Market Activity: Follow price changes in 1-hour increments throughout the trading day, making it easier to spot trends or reversals. Analyze Long-Term Intraday Patterns: Use 1-hour data to gain insights into the broader movements of currency pairs over the course of the trading day. Support Swing Trading Strategies: With hourly updates, this API is perfect for traders who operate in mid-term strategies, reacting to larger market trends. Whether you're actively trading or conducting market analysis, the 1-Hour Forex Interval Chart API helps provide the necessary data to make informed decisions based on evolving market conditions. Example Use Case A forex analyst looking to optimize their swing trading strategy uses the 1-Hour Forex Interval Chart API to track price movements of the USD/JPY pair. By monitoring hourly changes, the analyst identifies price consolidation points and adjusts their trades accordingly.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-chart/1hour?symbol=EURUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | EURUSD |
| from | date | 2024-01-01 |
| to | date | 2024-03-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 16:00:00",
    "open": 1.15254,
    "low": 1.1518,
    "high": 1.15263,
    "close": 1.15226,
    "volume": 3375
  }
]
```

---

# InsiderTrades

## Latest

### Latest Insider Trading

Access the latest insider trading activity using the Latest Insider Trading API. Track which company insiders are buying or selling stocks and analyze their transactions.

The FMP Latest Insider Trading API provides up-to-date information on insider trading activities. This API enables users to track recent stock purchases and sales by company insiders, including directors and executives. With details on transaction dates, types, and amounts, this API offers insights into corporate behavior and potential market trends. Key features include: Recent Insider Transactions: Access the most recent stock purchases or sales by company insiders. Transaction Details: Retrieve detailed information about the type of transaction, the number of shares transacted, and the price. Insider Roles: Identify the roles of the individuals involved in the transactions, such as directors or executives. Comprehensive Data: Access key information such as filing date, transaction date, type of ownership, and links to official filings. This API is ideal for investors, analysts, and financial researchers who want to track insider trading activity to assess market sentiment or potential investment opportunities. Example Use Case A hedge fund manager uses the Latest Insider Trading API to monitor recent stock purchases by company directors. By analyzing a purchase made by Larry Glasscock (director of SPG), they can assess whether the insider's buying activity signals confidence in the company&rsquo;s future performance and adjust their investment strategy accordingly.

**Endpoint:** `https://financialmodelingprep.com/stable/insider-trading/latest?page=0&limit=100`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| date | date | 2026-01-27 |
| page | number | 0 |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "WHF",
    "filingDate": "2026-06-05",
    "transactionDate": "2026-06-05",
    "reportingCik": "0001050047",
    "companyCik": "0001552198",
    "transactionType": "P-Purchase",
    "securitiesOwned": 309607,
    "reportingName": "BOLDUC JOHN",
    "typeOfOwner": "director",
    "acquisitionOrDisposition": "A",
    "directOrIndirect": "I",
    "formType": "4",
    "securitiesTransacted": 3570,
    "price": 6.77,
    "securityName": "Common Stock, par value $0.001 per share",
    "url": "https://www.sec.gov/Archives/edgar/data/1552198/000110465926071091/0001104659-26-071091-index.htm"
  }
]
```

---

## Search

### Search Insider Trades

Search insider trading activity by company or symbol using the Search Insider Trades API. Find specific trades made by corporate insiders, including executives and directors.

The FMP Search Insider Trades API allows users to search for specific insider trading activities based on a company or stock symbol. This API provides detailed information on stock transactions by corporate insiders, including transaction dates, types, amounts, and roles within the company. Key features include: Company-Specific Searches: Search insider trading activity by entering the stock symbol or company name to retrieve relevant transactions. Detailed Transaction Information: Access detailed data such as transaction type (purchase or sale), number of securities transacted, and price. Insider Roles: Understand the roles of the insiders involved in the transactions, such as directors or executives. Direct Links to Filings: Each transaction includes a link to the official SEC filing for deeper analysis and verification. This API is perfect for investors, financial researchers, and analysts who need to investigate insider trading activities of specific companies or individuals. Example Use Case An investment analyst uses the Search Insider Trades API to investigate recent sales of Apple (AAPL) stock by Chris Kondo, the Principal Accounting Officer. By retrieving detailed information about the transaction, including the sale of 8,706 shares at $225, the analyst can better assess the implications for the company&rsquo;s financial performance and strategy.

**Endpoint:** `https://financialmodelingprep.com/stable/insider-trading/search?page=0&limit=100`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol | string | AAPL |
| page | number | 0 |
| limit | number | 100 |
| reportingCik | string | 0001496686 |
| companyCik | string | 0000320193 |
| transactionType | string | S-Sale |

**Example Response**

```json
[
  {
    "symbol": "WHF",
    "filingDate": "2026-06-05",
    "transactionDate": "2026-06-05",
    "reportingCik": "0001050047",
    "companyCik": "0001552198",
    "transactionType": "P-Purchase",
    "securitiesOwned": 309607,
    "reportingName": "BOLDUC JOHN",
    "typeOfOwner": "director",
    "acquisitionOrDisposition": "A",
    "directOrIndirect": "I",
    "formType": "4",
    "securitiesTransacted": 3570,
    "price": 6.77,
    "securityName": "Common Stock, par value $0.001 per share",
    "url": "https://www.sec.gov/Archives/edgar/data/1552198/000110465926071091/0001104659-26-071091-index.htm"
  }
]
```

---

### Search Insider Trades by Reporting Name

Search for insider trading activity by reporting name using the Search Insider Trades by Reporting Name API. Track trading activities of specific individuals or groups involved in corporate insider transactions.

The FMP Search Insider Trades by Reporting Name API allows users to search for insider trading activities based on the name of a specific individual or group. This API provides key information such as the reporting CIK (Central Index Key) and the individual&rsquo;s name associated with insider transactions, enabling users to monitor the trading activity of high-profile individuals or corporate executives. Key features include: Name-Specific Searches: Easily search for insider trades by entering the name of a specific individual or entity. Reporting CIK Information: Retrieve the reporting CIK for more in-depth tracking of insider activity across filings. Track High-Profile Insiders: Monitor trades by well-known corporate executives, directors, or other insiders. Direct Access to Relevant Data: Quickly find information related to specific individuals&rsquo; insider trading activities, with links to more detailed data. This API is ideal for investors, analysts, and financial researchers who want to track insider trading activities associated with specific people or entities. Example Use Case A financial analyst uses the Search Insider Trades by Reporting Name API to track insider trading activity for Mark Zuckerberg. By retrieving the reporting CIK and related transactions, the analyst can monitor Zuckerberg&rsquo;s trading behavior and analyze how his actions might influence market sentiment regarding Meta Platforms.

**Endpoint:** `https://financialmodelingprep.com/stable/insider-trading/reporting-name?name=Zuckerberg`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| name* | string | Zuckerberg |

**Example Response**

```json
[
  {
    "reportingCik": "0001548760",
    "reportingName": "Zuckerberg Mark"
  }
]
```

---

## Statistics

### All Insider Transaction Types

Access a comprehensive list of insider transaction types with the All Insider Transaction Types API. This API provides details on various transaction actions, including purchases, sales, and other corporate actions involving insider trading.

The FMP All Insider Transaction Types API allows users to view all types of transactions made by corporate insiders. This includes purchases, sales, and other actions that insiders may take, such as options exercises or gifts. With this API, users can gain a comprehensive understanding of the different types of transactions insiders are reporting and their implications for company performance. Key features include: Comprehensive Transaction Coverage: View all types of insider transactions, including buying, selling, option exercises, and more. Transaction Classifications: Understand the classification of transactions, whether it's an acquisition, disposition, or other. Real-Time Insights: Stay updated on the latest insider actions and their potential impact on the company. Corporate Action Types: Access details on less common insider transactions, such as gifts or stock awards. This API is perfect for investors, analysts, and researchers who need to track a variety of insider trading actions to make more informed investment decisions. Example Use Case A market analyst uses the All Insider Transaction Types API to view a complete list of recent transactions by corporate insiders. By reviewing purchases, sales, and stock options exercised, the analyst can gain insights into corporate sentiment and make better-informed trading decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/insider-trading-transaction-type`

**Example Response**

```json
[
  {
    "transactionType": "A-Award"
  }
]
```

---

### Insider Trade Statistics

Analyze insider trading activity with the Insider Trade Statistics API. This API provides key statistics on insider transactions, including total purchases, sales, and trends for specific companies or stock symbols.

The FMP Insider Trade Statistics API provides comprehensive statistical data on insider trading activity for a specific stock symbol. This includes the total number of transactions, shares acquired or disposed of, and the overall ratio of acquisitions to dispositions. By analyzing these trends, users can gain insights into corporate sentiment and market behavior. Key features include: Transaction Breakdown: Access statistics on insider acquisitions and dispositions for a specific company. Acquired vs. Disposed Ratio: Analyze the ratio of shares acquired to shares disposed of, revealing insider sentiment. Quarterly Data: View insider trading activity on a quarterly basis, helping you track changes in trading patterns over time. Total and Average Transactions: Get detailed statistics on total purchases and sales, along with average transaction sizes. This API is ideal for investors, analysts, and financial researchers who need to analyze patterns and trends in insider trading activity to make informed investment decisions. Example Use Case A financial analyst uses the Insider Trade Statistics API to examine insider trading trends for Apple (AAPL) in the third quarter of 2024. By reviewing the ratio of shares disposed of to those acquired, along with the total number of sales, the analyst can assess whether insiders are showing confidence in the company&rsquo;s future.

**Endpoint:** `https://financialmodelingprep.com/stable/insider-trading/statistics?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "cik": "0000320193",
    "year": 2026,
    "quarter": 2,
    "acquiredTransactions": 5,
    "disposedTransactions": 35,
    "acquiredDisposedRatio": 0.1429,
    "totalAcquired": 272855,
    "totalDisposed": 880558,
    "averageAcquired": 54571,
    "averageDisposed": 25158.8,
    "totalPurchases": 0,
    "totalSales": 13
  }
]
```

---

## Acquisition Ownership

### Acquisition Ownership

Track changes in stock ownership during acquisitions using the Acquisition Ownership API. This API provides detailed information on how mergers, takeovers, or beneficial ownership changes impact the stock ownership structure of a company.

The FMP Acquisition Ownership API provides comprehensive data on changes in stock ownership during acquisitions, mergers, or other significant corporate events. It offers insight into how control and ownership are transferred or shared between entities, helping analysts and investors understand the impact of these changes on corporate governance and shareholder influence. Key features include: Ownership Changes: Track changes in beneficial ownership, including shared or sole voting and dispositive powers. Acquisition and Merger Data: View details about mergers, takeovers, or acquisitions that affect the ownership of company stock. Detailed Reporting Information: Access data about the reporting entities, including their CIK, name, and percentage of ownership. Filing Dates and SEC Links: Get links to official SEC filings and important dates related to acquisitions or ownership changes. This API is ideal for investors, financial analysts, and researchers who need to track how ownership structures shift during corporate acquisitions or mergers. Example Use Case An institutional investor uses the Acquisition Ownership API to monitor the impact of a recent merger involving Apple (AAPL). By examining the beneficial ownership change reported by National Indemnity Company, which now holds 755 million shares, the investor can assess how this affects voting power and control within the company.

**Endpoint:** `https://financialmodelingprep.com/stable/acquisition-of-beneficial-ownership?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| limit | number | 2000 |

**Example Response**

```json
[
  {
    "cik": "0000320193",
    "symbol": "AAPL",
    "filingDate": "2026-04-29",
    "acceptedDate": "2026-04-29",
    "cusip": "037833100",
    "nameOfReportingPerson": "Vanguard Capital Management",
    "citizenshipOrPlaceOfOrganization": "PENNSYLVANIA",
    "soleVotingPower": "0",
    "sharedVotingPower": "0",
    "soleDispositivePower": "0",
    "sharedDispositivePower": "0",
    "amountBeneficiallyOwned": "1099168953",
    "percentOfClass": "7.48",
    "typeOfReportingPerson": "IA",
    "url": "https://www.sec.gov/Archives/edgar/data/320193/000210011926000139/xslSCHEDULE_13G_X02/primary_doc.xml"
  }
]
```

---

# MarketPerformance

## Market Performance

### Market Sector Performance Snapshot

Get a snapshot of sector performance using the Market Sector Performance Snapshot API. Analyze how different industries are performing in the market based on average changes across sectors.

The FMP Market Sector Performance Snapshot API provides real-time insights into the performance of different sectors across various stock exchanges. This API allows users to track the average performance of industries like Basic Materials, Technology, Healthcare, and more, helping analysts and investors understand how different parts of the market are doing at any given moment. Key features include: Sector-Specific Performance Data: Access performance data for various sectors, including the average percentage change for each sector. Exchange-Specific Analysis: Analyze sector performance across specific exchanges such as NASDAQ, NYSE, and others. Daily Snapshots: Get daily updates on sector performance to track trends and market dynamics in real time. Cross-Industry Comparisons: Compare the performance of different sectors to identify growth or decline in key areas of the market. This API is ideal for financial analysts, portfolio managers, and traders who need to track sector-level performance to make informed investment decisions. Example Use Case A portfolio manager uses the Market Sector Performance Snapshot API to review how different sectors performed on NASDAQ on a specific date. By identifying that the Basic Materials sector experienced an average decline of -0.31%, the manager can adjust their sector allocations and shift their focus to outperforming industries.

**Endpoint:** `https://financialmodelingprep.com/stable/sector-performance-snapshot?date=2024-02-01`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| date* | string | 2024-02-01 |
| exchange | string | NASDAQ |
| sector | string | Energy |

**Example Response**

```json
[
  {
    "date": "2024-02-01",
    "sector": "Basic Materials",
    "exchange": "NASDAQ",
    "averageChange": -0.31481377464310634
  }
]
```

---

### Industry Performance Snapshot

Access detailed performance data by industry using the Industry Performance Snapshot API. Analyze trends, movements, and daily performance metrics for specific industries across various stock exchanges.

The FMP Industry Performance Snapshot API provides a daily overview of how specific industries are performing across major stock exchanges. This API delivers key data, such as average percentage changes for industries like Advertising Agencies, Healthcare Equipment, or Technology Services, allowing users to track and compare performance trends within specific sectors. Key features include: Industry-Level Performance Data: View average percentage changes for specific industries across major exchanges. Real-Time Market Insights: Analyze industry performance trends and movements in real time with daily updates. Exchange-Specific Data: Compare how different industries are performing on various stock exchanges like NASDAQ, NYSE, and others. In-Depth Industry Comparisons: Track and analyze the performance of specific industries to understand market trends and identify growth opportunities. This API is ideal for market analysts, portfolio managers, and investors who need to understand the performance dynamics of individual industries to guide investment strategies. Example Use Case A market analyst uses the Industry Performance Snapshot API to analyze the performance of the Advertising Agencies industry on a specific date, and finds that it posted an average gain of 3.87% on NASDAQ. This data helps the analyst recommend sector-specific investments and identify growth trends in the advertising sector.

**Endpoint:** `https://financialmodelingprep.com/stable/industry-performance-snapshot?date=2024-02-01`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| date* | string | 2024-02-01 |
| exchange | string | NASDAQ |
| industry | string | Biotechnology |

**Example Response**

```json
[
  {
    "date": "2024-02-01",
    "industry": "Advertising Agencies",
    "exchange": "NASDAQ",
    "averageChange": 3.8660194344955996
  }
]
```

---

### Historical Market Sector Performance

Access historical sector performance data using the Historical Market Sector Performance API. Review how different sectors have performed over time across various stock exchanges.

The FMP Historical Market Sector Performance API provides detailed historical data on the performance of market sectors, such as Energy, Technology, Healthcare, and others. This API allows users to track and analyze sector-specific trends over time, helping identify long-term patterns and market movements. Key features include: Historical Sector Performance: Access historical data on average percentage changes in various sectors over time. Exchange-Specific Data: Track how sectors have performed on different stock exchanges, including NASDAQ, NYSE, and others. Long-Term Market Trends: Analyze trends and sector performance data over extended periods, offering insights for long-term investment strategies. Cross-Sector Analysis: Compare the performance of multiple sectors to see how different areas of the market have evolved. This API is ideal for financial researchers, portfolio managers, and investors who need to review historical sector performance for trend analysis, sector rotation strategies, and long-term planning. Example Use Case An investor uses the Historical Market Sector Performance API to review the Energy sector&rsquo;s historical performance on NASDAQ. By analyzing data from a specific date, showing an average change of 0.64%, the investor can track the sector's performance over time and make more informed decisions about future investments in the Energy sector.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-sector-performance?sector=Energy`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| from | string | 2024-02-01 |
| exchange | string | NASDAQ |
| sector* | string | Energy |
| to | string | 2024-03-01 |

**Example Response**

```json
[
  {
    "date": "2024-03-01",
    "sector": "Energy",
    "exchange": "NASDAQ",
    "averageChange": 1.3989969286740689
  }
]
```

---

### Historical Industry Performance

Access historical performance data for industries using the Historical Industry Performance API. Track long-term trends and analyze how different industries have evolved over time across various stock exchanges.

The FMP Historical Industry Performance API provides detailed historical data on the performance of various industries, such as Biotechnology, Technology, Financial Services, and more. This API allows users to track industry-specific performance metrics over time, providing insights into long-term trends and movements within the market. Key features include: Industry-Level Historical Data: Access performance data for specific industries, including average percentage changes over time. Exchange-Specific Performance: View how industries have performed on major stock exchanges like NASDAQ, NYSE, and others. Long-Term Trend Analysis: Analyze historical data to identify long-term industry trends and market shifts. Cross-Industry Comparisons: Compare the performance of different industries over time to identify growth areas and declining sectors. This API is ideal for market analysts, portfolio managers, and investors who need to track industry-level performance trends to guide long-term investment strategies. Example Use Case A financial analyst uses the Historical Industry Performance API to track the historical performance of the Biotechnology industry on NASDAQ. By reviewing data from a specific date, showing an average gain of 1.15%, the analyst can assess how the industry has performed over time and determine if it aligns with their investment strategy.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-industry-performance?industry=Biotechnology`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| industry* | string | Biotechnology |
| exchange | string | NASDAQ |
| from | string | 2024-02-01 |
| to | string | 2024-03-01 |

**Example Response**

```json
[
  {
    "date": "2024-03-01",
    "industry": "Biotechnology",
    "exchange": "NASDAQ",
    "averageChange": 2.6143442556463383
  }
]
```

---

## PE Ratio

### Sector Pe Snapshot

Retrieve the price-to-earnings (P/E) ratios for various sectors using the Sector P/E Snapshot API. Compare valuation levels across sectors to better understand market valuations.

The FMP Sector P/E Snapshot API provides detailed data on the price-to-earnings (P/E) ratios of different market sectors, such as Basic Materials, Technology, Healthcare, and more. This API allows users to analyze sector-specific valuations, providing insights into how sectors are valued relative to their earnings. Key features include: P/E Ratio by Sector: Access up-to-date P/E ratios for various sectors, helping you compare their relative valuations. Exchange-Specific Data: View sector P/E ratios for specific exchanges, such as NASDAQ or NYSE. Daily Updates: Receive daily updates on sector P/E ratios to track changes in valuation levels over time. Valuation Comparisons: Compare the P/E ratios across multiple sectors to identify potential overvalued or undervalued sectors. This API is ideal for investors, analysts, and portfolio managers who need to assess sector valuations for investment decision-making and market analysis. Example Use Case A portfolio manager uses the Sector P/E Snapshot API to compare the P/E ratios of different sectors on NASDAQ. By seeing that the Basic Materials sector has a P/E ratio of 15.69, they can assess whether this sector is overvalued or undervalued relative to other sectors and adjust their portfolio accordingly.

**Endpoint:** `https://financialmodelingprep.com/stable/sector-pe-snapshot?date=2024-02-01`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| date* | string | 2024-02-01 |
| exchange | string | NASDAQ |
| sector | string | Energy |

**Example Response**

```json
[
  {
    "date": "2024-02-01",
    "sector": "Basic Materials",
    "exchange": "NASDAQ",
    "pe": 15.687711758428254
  }
]
```

---

### Industry Pe Snapshot

View price-to-earnings (P/E) ratios for different industries using the Industry P/E Snapshot API. Analyze valuation levels across various industries to understand how each is priced relative to its earnings.

The FMP Industry P/E Snapshot API provides detailed information on the price-to-earnings (P/E) ratios of various industries, such as Advertising Agencies, Technology, and Healthcare. This API enables users to compare industry-specific valuation levels across stock exchanges like NASDAQ and NYSE, offering insights into which industries are overvalued or undervalued. Key features include: P/E Ratios by Industry: Access the most recent P/E ratios for industries across major stock exchanges. Daily Updates: Get daily snapshots of industry P/E ratios, helping track changes in valuations over time. Exchange-Specific Data: Analyze how industries are valued on different exchanges, such as NASDAQ or NYSE. Cross-Industry Comparisons: Compare P/E ratios across industries to identify potential investment opportunities or risks. This API is perfect for investors, analysts, and financial professionals looking to evaluate industry-specific valuations for making informed investment decisions. Example Use Case An investor uses the Industry P/E Snapshot API to assess a specific industry on NASDAQ. Knowing the P/E ratio, the investor can determine if the industry is overvalued and adjust their portfolio accordingly.

**Endpoint:** `https://financialmodelingprep.com/stable/industry-pe-snapshot?date=2024-02-01`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| date* | string | 2024-02-01 |
| exchange | string | NASDAQ |
| industry | string | Biotechnology |

**Example Response**

```json
[
  {
    "date": "2024-02-01",
    "industry": "Advertising Agencies",
    "exchange": "NASDAQ",
    "pe": 71.09601665201151
  }
]
```

---

### Historical Sector PE

Access historical price-to-earnings (P/E) ratios for various sectors using the Historical Sector P/E API. Analyze how sector valuations have evolved over time to understand long-term trends and market shifts.

The FMP Historical Sector P/E API provides detailed historical data on the price-to-earnings (P/E) ratios of different sectors, such as Energy, Technology, and Healthcare. This API helps users track how sector valuations have changed over time, offering insights into long-term trends and shifts in market sentiment. Key features include: Historical P/E Ratios by Sector: Access historical P/E ratios for various sectors, allowing you to track valuation trends. Exchange-Specific Data: Analyze sector valuations on specific exchanges, such as NASDAQ or NYSE. Long-Term Analysis: Review historical data to identify sector trends and how valuations have evolved over time. Cross-Sector Comparisons: Compare P/E ratios across multiple sectors to better understand relative valuations and market shifts. This API is ideal for market analysts, portfolio managers, and investors who need to analyze sector-level valuation trends for long-term investment strategies. Example Use Case A portfolio manager uses the Historical Sector P/E API to review the historical P/E ratios of the Energy sector on NASDAQ. By examining the changes in P/E ratios over time, the manager can assess how the sector's valuation has evolved and make informed decisions about future investments.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-sector-pe?sector=Energy`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| from | string | 2024-02-01 |
| exchange | string | NASDAQ |
| sector* | string | Energy |
| to | string | 2024-03-01 |

**Example Response**

```json
[
  {
    "date": "2024-03-01",
    "sector": "Energy",
    "exchange": "NASDAQ",
    "pe": 5.4165892628211205
  }
]
```

---

### Historical Industry PE

Access historical price-to-earnings (P/E) ratios by industry using the Historical Industry P/E API. Track valuation trends across various industries to understand how market sentiment and valuations have evolved over time.

The FMP Historical Industry P/E API provides detailed historical data on the price-to-earnings (P/E) ratios of different industries, such as Biotechnology, Financial Services, and Consumer Goods. This API helps users track how industry valuations have changed over time, offering insights into long-term trends and market shifts. Key features include: Industry-Specific P/E Data: Access historical P/E ratios for specific industries, helping you track how valuations have evolved over time. Exchange-Specific Analysis: View industry P/E ratios across different exchanges, including NASDAQ, NYSE, and more. Long-Term Valuation Trends: Analyze historical data to identify valuation trends and shifts in market sentiment within industries. Cross-Industry Comparisons: Compare P/E ratios across multiple industries to understand which sectors are undervalued or overvalued. This API is ideal for investors, market analysts, and portfolio managers who need to assess industry-specific valuation trends to inform long-term investment strategies. Example Use Case A financial analyst uses the Historical Industry P/E API to review the historical P/E ratios of the Biotechnology industry on NASDAQ. By tracking how the P/E ratio has evolved over time, the analyst can determine whether the industry&rsquo;s current valuation reflects long-term market trends and decide if it's a good investment opportunity.

**Endpoint:** `https://financialmodelingprep.com/stable/historical-industry-pe?industry=Biotechnology`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| industry* | string | Biotechnology |
| exchange | string | NASDAQ |
| from | string | 2024-02-01 |
| to | string | 2024-03-01 |

**Example Response**

```json
[
  {
    "date": "2024-03-01",
    "industry": "Biotechnology",
    "exchange": "NASDAQ",
    "pe": 8.129037884885042
  }
]
```

---

## Market Leaders

### Biggest Stock Gainers

Track the stocks with the largest price increases using the Top Stock Gainers API. Identify the companies that are leading the market with significant price surges, offering potential growth opportunities.

The FMP Top Stock Gainers API provides real-time data on stocks that are experiencing the most significant price increases across major stock exchanges. This API allows users to track the top-performing stocks, helping traders and investors identify momentum and potential short-term or long-term opportunities. Key features include: Top Gainers List: Access a real-time list of the stocks with the highest price increases. Real-Time Price &amp; Percentage Changes: Track the current price, total price change, and percentage change for each stock. Exchange-Specific Data: View the top stock gainers on specific exchanges, such as NASDAQ, NYSE, and more. Company Information: Get key details on the leading companies, including their name, symbol, and price change information. This API is perfect for day traders, swing traders, and investors looking to capitalize on fast-moving stocks and market leaders. Example Use Case A trader uses the Top Stock Gainers API to find stocks with the highest price increases on NASDAQ. After identifying CBL International Limited (BANL), which experienced a 27.69% price increase, the trader can decide to take advantage of the momentum and incorporate the stock into their trading strategy.

**Endpoint:** `https://financialmodelingprep.com/stable/biggest-gainers`

**Example Response**

```json
[
  {
    "symbol": "MOTS",
    "price": 0.0002,
    "name": "Motus GI Holdings, Inc.",
    "change": 0.0001,
    "changesPercentage": 100,
    "exchange": "OTC"
  }
]
```

---

### Biggest Stock Losers

Access data on the stocks with the largest price drops using the Biggest Stock Losers API. Identify companies experiencing significant declines and track the stocks that are falling the fastest in the market.

The FMP Biggest Stock Losers API provides real-time data on stocks that have seen the most substantial price declines across various exchanges. This API enables users to identify underperforming companies and track major drops in stock prices, offering insights into potential short-term opportunities or risks. Key features include: Top Decliners List: Access a real-time list of stocks with the largest price drops across major exchanges. Real-Time Price Changes: Track current price data, total price changes, and percentage declines for each stock. Exchange-Specific Data: View the biggest stock decliners on exchanges like NASDAQ, NYSE, and others. Company Information: Get essential details about the companies, including their name, symbol, and exchange. This API is ideal for traders, analysts, and investors looking to track significant downward movements in the stock market for potential trading or investment strategies. Example Use Case A trader uses the Biggest Stock Losers API to identify stocks on NASDAQ experiencing rapid price declines. After spotting a 31.33% drop in iSun, Inc. (ISUN), the trader can assess whether to short the stock or consider it for a rebound play.

**Endpoint:** `https://financialmodelingprep.com/stable/biggest-losers`

**Example Response**

```json
[
  {
    "symbol": "SPEC",
    "price": 0.0002,
    "name": "Spectaire Holdings Inc.",
    "change": -0.002,
    "changesPercentage": -90.90909,
    "exchange": "OTC"
  }
]
```

---

### Top Traded Stocks

View the most actively traded stocks using the Top Traded Stocks API. Identify the companies experiencing the highest trading volumes in the market and track where the most trading activity is happening.

The FMP Top Traded Stocks API provides real-time data on the stocks with the highest trading volumes across major stock exchanges. This API allows users to monitor which stocks are drawing the most attention from traders and investors, offering valuable insights into market activity and liquidity. Key features include: Top Traded Stocks: Access a list of the most actively traded stocks based on trading volumes. Real-Time Volume Data: Track the trading volume, price changes, and percentage change for each stock. Exchange-Specific Data: Monitor the most actively traded stocks on specific exchanges, such as NASDAQ or NYSE. Company Information: Get essential details about the most traded companies, including their name, symbol, and trading volume. This API is ideal for traders, analysts, and investors who need to track trading activity and liquidity in the stock market to inform their trading or investment strategies. Example Use Case A day trader uses the Top Traded Stocks API to identify which stocks on NASDAQ are experiencing the highest trading volumes. After spotting iSun, Inc. (ISUN) with a significant trading volume, the trader can decide whether to enter a trade based on the stock&rsquo;s momentum and market interest.

**Endpoint:** `https://financialmodelingprep.com/stable/most-actives`

**Example Response**

```json
[
  {
    "symbol": "LUCY",
    "price": 1.85,
    "name": "Innovative Eyewear, Inc.",
    "change": 0.06,
    "changesPercentage": 3.35196,
    "exchange": "NASDAQ"
  }
]
```

---

# MarketHours

## Market Hours

### Global Exchange Market Hours

Retrieve trading hours for specific stock exchanges using the Global Exchange Market Hours API. Find out the opening and closing times of global exchanges to plan your trading strategies effectively.

The FMP Global Exchange Market Hours API provides essential information about the opening and closing hours of various stock exchanges around the world. This API helps users track when exchanges like NASDAQ, NYSE, and others are open for trading, along with information about the time zone and whether the market is currently open. Key features include: Trading Hours by Exchange: Access the opening and closing times for specific stock exchanges worldwide. Real-Time Market Status: Find out if the market is currently open or closed for trading. Time Zone Support: View exchange market hours in the local time zone of each exchange for accurate planning. Global Exchange Coverage: Get information on major stock exchanges, including NASDAQ, NYSE, and others. This API is ideal for traders, analysts, and investors who need to stay informed about market hours to manage their trading strategies across different regions.

**Endpoint:** `https://financialmodelingprep.com/stable/exchange-market-hours?exchange=NASDAQ`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| exchange* | string | NASDAQ |
| timestamp | string | 1769527402 |

**Example Response**

```json
[
  {
    "exchange": "NASDAQ",
    "name": "NASDAQ",
    "openingHour": "09:30 AM -04:00",
    "closingHour": "04:00 PM -04:00",
    "timezone": "America/New_York",
    "isMarketOpen": false
  }
]
```

---

### Holidays By Exchange

Retrieve a list of market holidays and non-trading days for a specific stock exchange using the Holidays By Exchange API. Plan your trading schedule by knowing exactly when exchanges like NASDAQ, NYSE, and others are closed.

**Endpoint:** `https://financialmodelingprep.com/stable/holidays-by-exchange?exchange=NASDAQ`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| exchange* | string | NASDAQ |
| from | date | 2025-04-27 |
| to | date | 2026-04-27 |

**Example Response**

```json
[
  {
    "exchange": "NASDAQ",
    "date": "2026-04-03",
    "name": "Good Friday",
    "isClosed": true,
    "adjOpenTime": null,
    "adjCloseTime": null
  }
]
```

---

### All Exchange Market Hours

View the market hours for all exchanges. Check when different markets are active.

**Endpoint:** `https://financialmodelingprep.com/stable/all-exchange-market-hours`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| timestamp | string | 1769527402 |

**Example Response**

```json
[
  {
    "exchange": "ASX",
    "name": "Australian Securities Exchange",
    "openingHour": "10:00 AM +10:00",
    "closingHour": "04:00 PM +10:00",
    "timezone": "Australia/Sydney",
    "isMarketOpen": true
  }
]
```

---

# TechnicalIndicators

## Technical Indicators

### Simple Moving Average

Arithmetic mean of an asset's closing prices over a fixed look-back window, smoothing short-term noise to expose the underlying trend.

The SMA is computed as the unweighted average of the last N closes for the requested timeframe. Traders use it to identify trend direction, define dynamic support and resistance, and generate crossover signals against price or against a second SMA of different length. Because every observation carries equal weight, the SMA reacts more slowly than weighted variants such as EMA or WMA.

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/sma?symbol=AAPL&periodLength=10&timeframe=1day`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| periodLength* | number | 10 |
| timeframe* | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from | date | 2026-03-01 |
| to | date | 2026-06-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 00:00:00",
    "open": 312.86,
    "high": 315.17,
    "low": 307.15,
    "close": 307.34,
    "volume": 65310502,
    "sma": 310.291
  }
]
```

---

### Exponential Moving Average

Moving average that applies exponentially decaying weights to past prices, making the line more responsive to recent moves than a simple SMA.

The EMA gives the most recent close the highest weight and decays older observations geometrically with smoothing factor 2 / (N + 1). It reacts to new information faster than the SMA, which makes it preferred for shorter-term crossover systems and momentum strategies, at the cost of being more sensitive to whipsaws in choppy markets.

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/ema?symbol=AAPL&periodLength=10&timeframe=1day`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| periodLength* | number | 10 |
| timeframe* | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from | date | 2026-03-01 |
| to | date | 2026-06-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 00:00:00",
    "open": 312.86,
    "high": 315.17,
    "low": 307.15,
    "close": 307.34,
    "volume": 65310502,
    "ema": 308.44057474678436
  }
]
```

---

### Weighted Moving Average

Moving average that assigns linearly decreasing weights to older prices, balancing the responsiveness of an EMA with a deterministic decay.

In a length-N WMA the most recent close is multiplied by N, the previous by N-1, and so on, with the sum divided by N(N+1)/2. The linear decay puts more emphasis on recent data than the SMA while remaining simpler and more predictable than the EMA, making the WMA useful when a clear, bounded weighting profile is desired.

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/wma?symbol=AAPL&periodLength=10&timeframe=1day`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| periodLength* | number | 10 |
| timeframe* | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from | date | 2026-03-01 |
| to | date | 2026-06-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 00:00:00",
    "open": 312.86,
    "high": 315.17,
    "low": 307.15,
    "close": 307.34,
    "volume": 65310502,
    "wma": 310.3487272727272
  }
]
```

---

### Double Exponential Moving Average

A faster, lag-reduced moving average defined as 2·EMA − EMA(EMA), designed to track price more closely than a standard EMA.

DEMA subtracts the EMA of an EMA from twice the EMA itself, which cancels much of the lag inherent to single-pass exponential smoothing. The result is a curve that hugs price during strong trends and turns earlier at reversals, which traders pair with EMA crossovers, MACD-style histograms, or trend filters for breakout systems.

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/dema?symbol=AAPL&periodLength=10&timeframe=1day`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| periodLength* | number | 10 |
| timeframe* | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from | date | 2026-03-01 |
| to | date | 2026-06-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 00:00:00",
    "open": 312.86,
    "high": 315.17,
    "low": 307.15,
    "close": 307.34,
    "volume": 65310502,
    "dema": 312.41959432990143
  }
]
```

---

### Triple Exponential Moving Average

A further lag-reduced moving average defined as 3·EMA − 3·EMA(EMA) + EMA(EMA(EMA)), tighter to price than both EMA and DEMA.

TEMA layers three EMAs in a way that cancels more lag than DEMA while preserving most of the smoothing benefits of an exponential filter. It is favoured by short-term trend followers who want fast trend confirmation, though its sharper turns also make it more prone to whipsaws in low-volatility regimes.

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/tema?symbol=AAPL&periodLength=10&timeframe=1day`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| periodLength* | number | 10 |
| timeframe* | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from | date | 2026-03-01 |
| to | date | 2026-06-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 00:00:00",
    "open": 312.86,
    "high": 315.17,
    "low": 307.15,
    "close": 307.34,
    "volume": 65310502,
    "tema": 310.28622027117757
  }
]
```

---

### Relative Strength Index

Momentum oscillator bounded between 0 and 100 that measures the speed and magnitude of recent price changes to flag overbought and oversold conditions.

RSI is computed from the average gains and losses over the chosen period, with classic thresholds of 70 (overbought) and 30 (oversold). Beyond extreme readings, traders watch for divergences against price, mid-line crossings around 50 as a trend filter, and shifts in the index's own range to confirm regime changes.

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/rsi?symbol=AAPL&periodLength=10&timeframe=1day`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| periodLength* | number | 10 |
| timeframe* | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from | date | 2026-03-01 |
| to | date | 2026-06-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 00:00:00",
    "open": 312.86,
    "high": 315.17,
    "low": 307.15,
    "close": 307.34,
    "volume": 65310502,
    "rsi": 56.87420287286961
  }
]
```

---

### Standard Deviation

Rolling measure of price dispersion around its mean over a fixed window, used as a fundamental gauge of volatility for the requested asset and timeframe.

The endpoint computes the standard deviation of closing prices over the supplied period length, sampled at the chosen timeframe. It underpins volatility-based tools such as Bollinger Bands, position-sizing models, and risk filters, and is often used directly to detect volatility regime shifts or to normalise other indicators.

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/standarddeviation?symbol=AAPL&periodLength=10&timeframe=1day`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| periodLength* | number | 10 |
| timeframe* | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from | date | 2026-03-01 |
| to | date | 2026-06-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 00:00:00",
    "open": 312.86,
    "high": 315.17,
    "low": 307.15,
    "close": 307.34,
    "volume": 65310502,
    "standardDeviation": 2.5280998793560374
  }
]
```

---

### Williams

Momentum oscillator bounded between -100 and 0 that locates the current close relative to the highest high and lowest low of the look-back window.

Williams %R reads -20 or above as overbought and -80 or below as oversold, mirroring the structure of the Stochastic but using only highs and lows. It is well suited for identifying short-term exhaustion in trending markets, especially when combined with a longer-term trend filter to avoid taking countertrend signals.

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/williams?symbol=AAPL&periodLength=10&timeframe=1day`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| periodLength* | number | 10 |
| timeframe* | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from | date | 2026-03-01 |
| to | date | 2026-06-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 00:00:00",
    "open": 312.86,
    "high": 315.17,
    "low": 307.15,
    "close": 307.34,
    "volume": 65310502,
    "williams": -80.53691275167793
  }
]
```

---

### Average Directional Index

Indicator measuring trend strength on a 0–100 scale, derived from smoothed directional movement and used to separate trending markets from ranging ones.

ADX is the smoothed average of the absolute difference between the +DI and -DI directional indicators over the chosen period. Readings above 25 typically signal a developing trend and above 40 a strong one, while sustained values below 20 suggest a range-bound market. The indicator describes strength only — direction is read from the +DI / -DI pair.

**Endpoint:** `https://financialmodelingprep.com/stable/technical-indicators/adx?symbol=AAPL&periodLength=10&timeframe=1day`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| periodLength* | number | 10 |
| timeframe* | string | 1min,5min,15min,30min,1hour,4hour,1day |
| from | date | 2026-03-01 |
| to | date | 2026-06-01 |

**Example Response**

```json
[
  {
    "date": "2026-06-05 00:00:00",
    "open": 312.86,
    "high": 315.17,
    "low": 307.15,
    "close": 307.34,
    "volume": 65310502,
    "adx": 54.65170078857176
  }
]
```

---

# News

## Articles

### FMP Articles

Access the latest articles from FMP with the FMP Articles API. Get comprehensive updates including headlines, snippets, and publication URLs.

The FMP Articles API provides access to a curated list of the most recent articles published by FMP. This endpoint offers: Headlines: Stay informed with the latest headlines covering a wide range of financial topics. Snippets: Quickly grasp the key points of each article with concise snippets. Publication URLs: Access the full articles through provided URLs for in-depth reading. This API is updated regularly to ensure you have access to the most current content, helping you stay informed about the latest trends, insights, and analyses from FMP.

**Endpoint:** `https://financialmodelingprep.com/stable/fmp-articles?page=0&limit=20`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| page | number | 0 |
| limit | number | 20 |

**Example Response**

```json
[
  {
    "title": "Meta Platforms (NASDAQ:META) Faces Downgrade Amidst AI Investment and Potential Stock Offering",
    "date": "2026-06-05 20:23:22",
    "content": "<ul>\n    <li><strong>Citigroup Downgrade:</strong> <a href=\"https://site.financialmodelingprep.com/financial-summary/META\">Meta Platforms (NASDAQ:META)</a> received an \"Underweight\" rating from Citigroup, signaling concerns about its aggressive artificial intelligence investments.</li>\n    <li><strong>Potential Stock Offering:</strong> Reports indicate Meta Platforms may issue new shares to raise tens of billions of dollars, earmarked for funding its substantial AI infrastructure development.</l...",
    "tickers": "NASDAQ:META",
    "image": "https://portal.financialmodelingprep.com/positions/6a233af3d100e6cbf386bb06.jpeg",
    "link": "https://financialmodelingprep.com/market-news/meta-platforms-meta-downgraded-ai-costs-offering",
    "author": "Alex Lavoie",
    "site": "Financial Modeling Prep"
  }
]
```

---

### General News

Access the latest general news articles from a variety of sources with the FMP General News API. Obtain headlines, snippets, and publication URLs for comprehensive news coverage.

The FMP General News API provides access to the latest general news articles from a wide range of sources. This endpoint includes: Headlines: Stay informed with the latest headlines on current events. Snippets: Get brief summaries of the articles to quickly understand the key points. Publication URLs: Access full articles through provided URLs for detailed information. This API is updated daily to ensure you have the most current news. Simply provide the date range you are interested in, and the endpoint will return a list of all general news articles published during that period.

**Endpoint:** `https://financialmodelingprep.com/stable/news/general-latest?page=0&limit=20`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| from | date | 2026-01-27 |
| to | date | 2026-04-28 |
| page | number | 0 |
| limit | number | 20 |

**Example Response**

```json
[
  {
    "symbol": null,
    "publishedDate": "2026-06-06 12:40:12",
    "publisher": "Reuters",
    "title": "Deferring jet orders over Iran war would be costly for Middle Eastern carriers, IATA VP says",
    "image": "https://images.financialmodelingprep.com/news/deferring-jet-orders-over-iran-war-would-be-costly-20260606.jpg",
    "site": "reuters.com",
    "text": "Deferring jet orders due to uncertainty and higher jet fuel prices caused by the war in Iran would ​be unwise for Middle Eastern carriers, as the decision could be costly ‌in the long term, a vice president of the airline trade group IATA said on Saturday.",
    "url": "https://www.reuters.com/business/aerospace-defense/deferring-jet-orders-over-iran-war-would-be-costly-middle-eastern-carriers-iata-2026-06-06/"
  }
]
```

---

### Press Releases

Access official company press releases with the FMP Press Releases API. Get real-time updates on corporate announcements, earnings reports, mergers, and more.

The Press Releases API provides real-time access to official company announcements, allowing investors, analysts, and business professionals to stay informed on the latest developments. This API is crucial for: Company Announcements: Stay informed about earnings reports, product launches, mergers, and more directly from companies. Strategic Updates: Track leadership changes, business restructuring, and other significant corporate strategies that may affect a company's market standing. Market Impact Analysis: Analyze how company press releases influence stock prices, company valuations, and market sentiment. This API ensures that you have access to the most current press releases, helping you make informed decisions based on the latest corporate disclosures. Example Use Case A financial analyst uses the Press Releases API to monitor corporate announcements from publicly traded companies, providing critical insights for investment decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/news/press-releases-latest?page=0&limit=20`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| from | date | 2026-01-27 |
| to | date | 2026-04-28 |
| page | number | 0 |
| limit | number | 20 |

**Example Response**

```json
[
  {
    "symbol": "GPK",
    "publishedDate": "2026-06-06 15:00:00",
    "publisher": "GlobeNewsWire",
    "title": "ROSEN, NATIONAL INVESTOR COUNSEL, Encourages Graphic Packaging Holding Company Investors to Secure Counsel Before Important Deadline in Securities Class Action – GPK",
    "image": "https://images.financialmodelingprep.com/news/rosen-national-investor-counsel-encourages-graphic-packaging-holding-company-20260606.jpg",
    "site": "globenewswire.com",
    "text": "NEW YORK, June 06, 2026 (GLOBE NEWSWIRE) -- WHY: Rosen Law Firm, a global investor rights law firm, reminds purchasers of securities of Graphic Packaging Holding Company (NYSE: GPK) between February 4, 2025 and February 2, 2026, inclusive (the “Class Period”), of the important July 6, 2026 lead plaintiff deadline.",
    "url": "https://www.globenewswire.com/news-release/2026/06/06/3307694/673/en/ROSEN-NATIONAL-INVESTOR-COUNSEL-Encourages-Graphic-Packaging-Holding-Company-Investors-to-Secure-Counsel-Before-Important-Deadline-in-Securities-Class-Action-GPK.html"
  }
]
```

---

### Stock News

Stay informed with the latest stock market news using the FMP Stock News Feed API. Access headlines, snippets, publication URLs, and ticker symbols for the most recent articles from a variety of sources.

The Stock News API offers up-to-date information on stock market events, keeping traders, investors, and financial professionals informed about: Breaking Market News: Access the latest headlines that may impact stock prices and market movements. Company-Specific News: Stay updated on news related to individual stocks, including earnings reports, product announcements, and mergers. Market Trends and Analysis: Follow broader market trends and sentiment to make better investment decisions. This API is designed to provide timely news that helps professionals track stock market developments and make informed decisions. Example Use Case A portfolio manager uses the Stock News API to track real-time updates on the stock markets, ensuring they are aware of any news that may affect the performance of the equities in their portfolio.

**Endpoint:** `https://financialmodelingprep.com/stable/news/stock-latest?page=0&limit=20`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| from | date | 2026-01-27 |
| to | date | 2026-04-28 |
| page | number | 0 |
| limit | number | 20 |

**Example Response**

```json
[
  {
    "symbol": "LASR",
    "publishedDate": "2026-06-06 15:05:07",
    "publisher": "Forbes",
    "title": "This Small-Cap Manager Is Up 94%, Betting On Hidden Drivers In The New Economy",
    "image": "https://images.financialmodelingprep.com/news/this-smallcap-manager-is-up-94-betting-on-hidden-20260606.jpg",
    "site": "forbes.com",
    "text": "Lasers that can shoot down drones. Data center infrastructure powering artificial intelligence.",
    "url": "https://www.forbes.com/sites/sergeiklebnikov/2026/06/06/this-small-cap-manager-is-up-94-betting-on-hidden-drivers-in-the-new-economy/"
  }
]
```

---

### Crypto News

Stay informed with the latest cryptocurrency news using the FMP Crypto News API. Access a curated list of articles from various sources, including headlines, snippets, and publication URLs.

The Crypto News API provides up-to-date news on cryptocurrencies, including key market events and trends. This API is critical for: Real-Time Updates: Receive the latest news on major cryptocurrencies like Bitcoin, Ethereum, and more. Market Sentiment Analysis: Follow news and reports that could influence crypto market sentiment and price movements. Cryptocurrency Trends: Stay informed about industry developments, new technologies, and regulatory updates. This API is a must-have for anyone involved in the fast-moving world of cryptocurrency investing and trading. Example Use Case A crypto trader uses the Crypto News API to track daily news on Bitcoin and Ethereum, enabling them to stay ahead of market trends.

**Endpoint:** `https://financialmodelingprep.com/stable/news/crypto-latest?page=0&limit=20`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| from | date | 2026-01-27 |
| to | date | 2026-04-28 |
| page | number | 0 |
| limit | number | 20 |

**Example Response**

```json
[
  {
    "symbol": "BTCUSD",
    "publishedDate": "2026-06-06 15:37:10",
    "publisher": "Blockonomi",
    "title": "Beyond Bitcoin's Price: Why BitMEX Research Defends Michael Saylor's Strategy Model",
    "image": "https://images.financialmodelingprep.com/news/beyond-bitcoins-price-why-bitmex-research-defends-michael-saylors-20260606.webp",
    "site": "blockonomi.com",
    "text": "BitMEX says Arkham BTC spend analysis ignores equity-driven value created via premium stock issuance",
    "url": "https://blockonomi.com/beyond-bitcoins-price-why-bitmex-research-defends-michael-saylors-strategy-model/"
  }
]
```

---

### Forex News

Stay updated with the latest forex news articles from various sources using the FMP Forex News API. Access headlines, snippets, and publication URLs for comprehensive market insights.

The Forex News API provides up-to-date reports on currency markets, ensuring you stay informed about: Currency Market Movements: Get real-time updates on the forex market, including major events and macro-economic trends that influence currency pairs. Currency Pair Analysis: Stay informed on specific currency pair movements, such as EUR/USD, GBP/USD, or JPY/CHF, to better understand market conditions. Market Sentiment Updates: Follow forex-related news to gauge investor sentiment and market dynamics in the foreign exchange sector. This API is essential for traders, analysts, and financial professionals who need to stay on top of the ever-changing forex markets. Example Use Case A forex trader uses the Forex News API to track the latest news on currency pairs, helping them make quick and informed trading decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/news/forex-latest?page=0&limit=20`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| from | date | 2026-01-27 |
| to | date | 2026-04-28 |
| page | number | 0 |
| limit | number | 20 |

**Example Response**

```json
[
  {
    "symbol": "XAGUSD",
    "publishedDate": "2026-06-06 06:36:02",
    "publisher": "FXEmpire",
    "title": "Silver (XAG) Forecast: Margin Calls Send Silver Prices Sharply Lower",
    "image": "https://images.financialmodelingprep.com/news/silver-xag-forecast-margin-calls-send-silver-prices-sharply-lower-20260606.jpg",
    "site": "fxempire.com",
    "text": "Silver prices plunged 8% after strong U.S. jobs data boosted rate hike expectations, triggering margin call selling and testing key support levels.",
    "url": "https://www.fxempire.com/forecasts/article/silver-xag-forecast-margin-calls-send-silver-prices-sharply-lower-1602869"
  }
]
```

---

## Symbol

### Search Press Releases

Search for company press releases with the FMP Search Press Releases API. Find specific corporate announcements and updates by entering a stock symbol or company name.

The Search Press Releases API allows users to find specific press releases based on a company name or stock symbol, offering quick access to relevant announcements. This API is essential for: Targeted Searches: Narrow down your search to find exact press releases from a particular company. Symbol-Based Retrieval: Use stock symbols to pinpoint corporate disclosures, making it ideal for investors and analysts looking for precise data. Historical and Real-Time Access: Retrieve both current and past press releases, helping with long-term trend analysis. This API is designed for professionals who need quick, reliable access to specific press releases, saving time and providing accurate data. Example Use Case An investor uses the Search Press Releases API to find the most recent earnings report of a specific company before making an investment decision.

**Endpoint:** `https://financialmodelingprep.com/stable/news/press-releases?symbols=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbols* | string | AAPL |
| from | date | 2026-01-27 |
| to | date | 2026-04-28 |
| page | number | 0 |
| limit | number | 20 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "publishedDate": "2026-06-04 23:17:00",
    "publisher": "GlobeNewsWire",
    "title": "Iron Age Nutrition Announces Launch of “Sour Apple Crush” Flavor in Total Hydrate Electrolyte Line",
    "image": "https://images.financialmodelingprep.com/news/iron-age-nutrition-announces-launch-of-sour-apple-crush-20260604.jpg",
    "site": "globenewswire.com",
    "text": "FORT LAUDERDALE, FL, June 04, 2026 (GLOBE NEWSWIRE) -- Iron Age Nutrition announced the introduction of “Sour Apple Crush,” a new flavor within its Total Hydrate electrolyte line. The addition expands the company's existing portfolio of electrolyte stick packets offered in single-serve format. According to the company, the new flavor features a sour green apple-inspired profile and is now available through ironagenutrition.com. Sour Apple Crush is offered in 12-pack and 24-pack configurations of individual stick packets, with pricing listed at $19.99 and $35.99, respectively.",
    "url": "https://www.globenewswire.com/news-release/2026/06/05/3307178/0/en/Iron-Age-Nutrition-Announces-Launch-of-Sour-Apple-Crush-Flavor-in-Total-Hydrate-Electrolyte-Line.html"
  }
]
```

---

### Search Stock News

Search for stock-related news using the FMP Search Stock News API. Find specific stock news by entering a ticker symbol or company name to track the latest developments.

The Search Stock News API helps users find stock-related news by entering a specific company name or stock symbol. This tool is ideal for: Targeted News Searches: Narrow down your search to find news about specific companies or stocks. Symbol-Based Lookup: Quickly retrieve news by entering the relevant ticker symbol for a stock. Comprehensive News Retrieval: Access both current and historical news reports to gain a full picture of stock movements over time. This API is tailored for investors and analysts who require fast, reliable access to news affecting specific stocks. Example Use Case A trader uses the Search Stock News API to look up recent news articles about a stock they are considering buying, helping them make an informed decision.

**Endpoint:** `https://financialmodelingprep.com/stable/news/stock?symbols=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbols* | string | AAPL |
| from | date | 2026-01-27 |
| to | date | 2026-04-28 |
| page | number | 0 |
| limit | number | 20 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "publishedDate": "2026-06-06 14:13:36",
    "publisher": "TechCrunch",
    "title": "What to expect from WWDC 2026: Siri's highly anticipated revamp and Apple Intelligence updates",
    "image": "https://images.financialmodelingprep.com/news/what-to-expect-from-wwdc-2026-siris-highly-anticipated-20260606.jpg",
    "site": "techcrunch.com",
    "text": "As Apple's Worldwide Developers Conference, WWDC 2026, approaches, the excitement is building around what Apple has in store for us this year. From Siri's overhaul to new Apple Intelligence updates, there's a lot to look forward to.",
    "url": "https://techcrunch.com/2026/06/06/what-to-expect-from-wwdc-2026-siris-highly-anticipated-revamp-and-apple-intelligence-updates/"
  }
]
```

---

### Search Crypto News

Search for cryptocurrency news using the FMP Search Crypto News API. Retrieve news related to specific coins or tokens by entering their name or symbol.

The Search Crypto News API allows users to look up cryptocurrency news by entering a coin name or symbol. This API is helpful for: Targeted Searches: Quickly find news on specific cryptocurrencies by entering their name or ticker symbol. Real-Time &amp; Historical News: Retrieve both current and past news on digital assets to track market trends and price drivers. Symbol-Based Lookups: Find news related to your preferred coins, such as Bitcoin (BTC) or Ethereum (ETH). This API is ideal for cryptocurrency investors who need fast access to news that could affect the value of their digital assets. Example Use Case A crypto investor uses the Search Crypto News API to search for news on Ethereum to understand the recent market movements before making a trade.

**Endpoint:** `https://financialmodelingprep.com/stable/news/crypto?symbols=BTCUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbols* | string | BTCUSD |
| from | date | 2026-01-27 |
| to | date | 2026-04-28 |
| page | number | 0 |
| limit | number | 20 |

**Example Response**

```json
[
  {
    "symbol": "BTCUSD",
    "publishedDate": "2026-06-06 15:37:10",
    "publisher": "Blockonomi",
    "title": "Beyond Bitcoin's Price: Why BitMEX Research Defends Michael Saylor's Strategy Model",
    "image": "https://images.financialmodelingprep.com/news/beyond-bitcoins-price-why-bitmex-research-defends-michael-saylors-20260606.webp",
    "site": "blockonomi.com",
    "text": "BitMEX says Arkham BTC spend analysis ignores equity-driven value created via premium stock issuance",
    "url": "https://blockonomi.com/beyond-bitcoins-price-why-bitmex-research-defends-michael-saylors-strategy-model/"
  }
]
```

---

### Search Forex News

Search for foreign exchange news using the FMP Search Forex News API. Find targeted news on specific currency pairs by entering their symbols for focused updates.

The Search Forex News API allows users to look up forex news by entering a currency pair, such as EUR/USD or GBP/USD. This API is perfect for: Targeted News Search: Easily find news about specific currency pairs to track the latest developments in the forex market. Historical News Access: Look up both current and historical forex news to analyze long-term trends and market movements. Symbol-Based Retrieval: Enter specific currency pair symbols to retrieve relevant news for informed decision-making. This API is ideal for forex traders who need quick access to news related to specific currency pairs. Example Use Case A currency trader uses the Search Forex News API to search for the latest news on EUR/USD, helping them understand recent price fluctuations before entering a trade.

**Endpoint:** `https://financialmodelingprep.com/stable/news/forex?symbols=EURUSD`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbols* | string | EURUSD |
| from | date | 2026-01-27 |
| to | date | 2026-04-28 |
| page | number | 0 |
| limit | number | 20 |

**Example Response**

```json
[
  {
    "symbol": "EURUSD",
    "publishedDate": "2026-06-05 12:45:35",
    "publisher": "FXEmpire",
    "title": "U.S. Dollar Soars As Non Farm Payrolls Beat Estimates: Analysis For EUR/USD, GBP/USD, USD/CAD, USD/JPY",
    "image": "https://images.financialmodelingprep.com/news/us-dollar-soars-as-non-farm-payrolls-beat-estimates-20260605.jpg",
    "site": "fxempire.com",
    "text": "The American currency tests multi-week highs as traders bet on hawkish Fed.",
    "url": "https://www.fxempire.com/forecasts/article/u-s-dollar-soars-as-non-farm-payrolls-beat-estimates-analysis-for-eur-usd-gbp-usd-usd-cad-usd-jpy-1602771"
  }
]
```

---

# Quote

## Single Quote

### Stock Quote

Access real-time stock quotes with the FMP Stock Quote API. Get up-to-the-minute prices, changes, and volume data for individual stocks.

The FMP Stock Quote API provides detailed, real-time stock data for individual stocks, making it a valuable tool for investors, traders, and financial analysts. This API helps you: Monitor Real-Time Prices: Stay updated with the latest stock prices to make informed trading decisions. Analyze Stock Movements: Track key data points such as price changes, volume, day highs and lows, and yearly highs and lows. Portfolio Tracking: Use real-time data to keep track of stock performance in your portfolio. Whether you are monitoring individual stocks or building trading strategies, this API ensures that you have the most up-to-date information.

**Endpoint:** `https://financialmodelingprep.com/stable/quote?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "price": 232.8,
    "changePercentage": 2.1008,
    "change": 4.79,
    "volume": 44489128,
    "dayLow": 226.65,
    "dayHigh": 233.13,
    "yearHigh": 260.1,
    "yearLow": 164.08,
    "marketCap": 3500823120000,
    "priceAvg50": 240.2278,
    "priceAvg200": 219.98755,
    "exchange": "NASDAQ",
    "open": 227.2,
    "previousClose": 228.01,
    "timestamp": 1738702801
  }
]
```

---

### Stock Quote Short

Get quick snapshots of real-time stock quotes with the FMP Stock Quote Short API. Access key stock data like current price, volume, and price changes for instant market insights.

The FMP Stock Quote Short API provides a concise, real-time snapshot of essential stock information, making it perfect for quick checks and streamlined data retrieval. This API is ideal for: Quick Stock Monitoring: Get key data such as current stock price, price change, and trading volume with minimal delay. High-Frequency Trading: Traders looking for rapid updates can use this API to stay ahead of the market in a streamlined format. Simplified Data Feed: For applications requiring lightweight data, the short format is efficient and easy to integrate. This API delivers the core metrics you need to make fast, informed trading decisions without unnecessary data points.

**Endpoint:** `https://financialmodelingprep.com/stable/quote-short?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "price": 232.8,
    "change": 4.79,
    "volume": 44489128
  }
]
```

---

### Aftermarket Trade

Track real-time trading activity occurring after regular market hours with the FMP Aftermarket Trade API. Access key details such as trade prices, sizes, and timestamps for trades executed during the post-market session.

The FMP Aftermarket Trade API allows investors to monitor trades made outside of standard market hours, offering insights into post-market trading activity. This API is ideal for: After-Hours Monitoring: Stay informed about stock prices and trading activity in the aftermarket session to track price movements outside the main trading day. Investor Insights: Detect trends or patterns in aftermarket trades that could provide valuable information ahead of the next trading session. Enhanced Trading Strategies: Use aftermarket data to adjust trading strategies for the next day or make more informed decisions based on overnight market activity. This API helps users gain visibility into the post-market period, enabling more comprehensive tracking of market activity outside traditional trading hours.

**Endpoint:** `https://financialmodelingprep.com/stable/aftermarket-trade?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "price": 232.53,
    "tradeSize": 132,
    "timestamp": 1738715334311
  }
]
```

---

### Aftermarket Quote

Access real-time aftermarket stock quotes with the FMP Aftermarket Quote API. Track bid and ask prices, volume, and other relevant data outside of regular trading hours.

The FMP Aftermarket Stock Quote API provides comprehensive quotes for stocks traded outside of normal market hours. This API is essential for: Tracking Aftermarket Stock Movers: See real-time bid and ask prices, volumes, and other key metrics after the stock market closes. Strategic Analysis: Use aftermarket stock quotes to gain insights into market sentiment and stock performance beyond regular trading hours, helping you make better decisions for the next trading session. Efficient Market Monitoring: Stay updated on price movements and trends that can affect next-day trading strategies. With the Aftermarket Stock Price API, investors can efficiently monitor post-market movements, bid-ask spreads, and trading volumes to stay ahead of potential shifts in the market.

**Endpoint:** `https://financialmodelingprep.com/stable/aftermarket-quote?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "bidSize": 1,
    "bidPrice": 232.45,
    "askSize": 3,
    "askPrice": 232.64,
    "volume": 41647042,
    "timestamp": 1738715334311
  }
]
```

---

### Stock Price Change

Track stock price fluctuations in real-time with the FMP Stock Price Change API. Monitor percentage and value changes over various time periods, including daily, weekly, monthly, and long-term.

The FMP Stock Price Change API allows you to stay updated on the real-time performance of stocks by tracking price changes across multiple timeframes. This API is essential for: Real-Time Monitoring: Track percentage and value changes in stock prices over different time intervals, such as 1 day, 5 days, 1 month, and up to 10 years. Investment Strategy: Use the data to identify trends in stock performance, helping you make informed decisions based on short-term and long-term price movements. Comparative Analysis: Compare price changes across multiple timeframes to assess a stock&rsquo;s performance over time, helping you adjust your portfolio or strategy accordingly. This API is a valuable resource for investors, traders, and analysts who need detailed stock performance data to inform their strategies and decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/stock-price-change?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "1D": 2.1008,
    "5D": -2.45946,
    "1M": -4.33925,
    "3M": 4.86014,
    "6M": 5.88556,
    "ytd": -4.53147,
    "1Y": 24.04092,
    "3Y": 35.04264,
    "5Y": 192.05871,
    "10Y": 678.8558,
    "max": 181279.04168
  }
]
```

---

## Batch

### Stock Batch Quote

Retrieve multiple real-time stock quotes in a single request with the FMP Stock Batch Quote API. Access current prices, volume, and detailed data for multiple companies at once, making it easier to track large portfolios or monitor multiple stocks simultaneously.

The FMP Stock Batch Quote API allows users to retrieve quotes for multiple stocks in one streamlined request. This API is ideal for: Portfolio Monitoring: Track several stocks in real-time, perfect for investors or portfolio managers who need to monitor multiple holdings at once. Data Efficiency: Instead of making multiple calls, get detailed stock data for several companies in a single API request, reducing complexity. Comprehensive Stock Insights: Access detailed data for each stock, including the current price, volume, day high/low, 50-day and 200-day moving averages, and more. This API ensures efficient data retrieval for investors, traders, and applications requiring comprehensive real-time stock data for multiple symbols.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-quote?symbols=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbols* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "price": 232.8,
    "changePercentage": 2.1008,
    "change": 4.79,
    "volume": 44489128,
    "dayLow": 226.65,
    "dayHigh": 233.13,
    "yearHigh": 260.1,
    "yearLow": 164.08,
    "marketCap": 3500823120000,
    "priceAvg50": 240.2278,
    "priceAvg200": 219.98755,
    "exchange": "NASDAQ",
    "open": 227.2,
    "previousClose": 228.01,
    "timestamp": 1738702801
  }
]
```

---

### Stock Batch Quote Short

Access real-time, short-form quotes for multiple stocks with the FMP Stock Batch Quote Short API. Get a quick snapshot of key stock data such as current price, change, and volume for several companies in one streamlined request.

The FMP Stock Batch Quote Short API is designed for users who need quick, high-level data for multiple stocks in one go. This API is ideal for: Quick Price Monitoring: Get a snapshot of current prices, changes, and volume for several stocks at once, helping you keep tabs on market trends. Portfolio Efficiency: Track essential stock data for multiple holdings in a single request, perfect for portfolio managers or traders who need rapid updates. Streamlined Data Retrieval: Skip the detailed data and focus on the basics&mdash;price, change, and volume&mdash;giving you the key insights quickly and efficiently. This API provides a fast and efficient way to monitor key stock information for multiple companies, all in one simple request.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-quote-short?symbols=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbols* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "price": 232.8,
    "change": 4.79,
    "volume": 44489128
  }
]
```

---

### Batch Aftermarket Trade

Retrieve real-time aftermarket trading data for multiple stocks with the FMP Batch Aftermarket Trade API. Track post-market trade prices, volumes, and timestamps across several companies simultaneously.

The FMP Batch Aftermarket Trade API provides detailed aftermarket trading data for multiple stocks in a single request. This API is perfect for: Monitoring Multiple Stocks: Stay updated on post-market trades for various companies, allowing you to track price movements and trading activity after regular market hours. Efficient Data Access: Instead of retrieving data for each stock individually, this API lets you access aftermarket trading information for a batch of stocks all at once. Enhanced Investment Decisions: Use real-time data from the aftermarket session to analyze trends or patterns across multiple stocks, helping you prepare for the next trading day. With this API, investors can efficiently track post-market activity for several stocks, enabling more comprehensive analysis and strategy adjustments.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-aftermarket-trade?symbols=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbols* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "price": 232.53,
    "tradeSize": 132,
    "timestamp": 1738715334311
  }
]
```

---

### Batch Aftermarket Quote

Retrieve real-time aftermarket quotes for multiple stocks with the FMP Batch Aftermarket Quote API. Access bid and ask prices, volume, and other relevant data for several companies during post-market trading.

The FMP Batch Aftermarket Quote API allows you to efficiently track aftermarket trading activity for multiple stocks at once. This API is ideal for: Monitoring Multiple Stocks: Get bid and ask prices, volume, and other key aftermarket data for several stocks simultaneously, providing a comprehensive view of post-market movements. Post-Market Strategy: Use batch data to analyze stock performance and develop strategies based on aftermarket trends that can affect the next trading session. Streamlined Data Access: Track the aftermarket trading environment across your portfolio or watchlist in one single request. The Batch Aftermarket Quote API helps investors make quicker, more informed decisions by providing real-time data on several stocks after normal market hours.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-aftermarket-quote?symbols=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbols* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "bidSize": 1,
    "bidPrice": 232.45,
    "askSize": 3,
    "askPrice": 232.64,
    "volume": 41647042,
    "timestamp": 1738715334311
  }
]
```

---

## Batch List

### Exchange Stock Quotes

Retrieve real-time stock quotes for all listed stocks on a specific exchange with the FMP Exchange Stock Quotes API. Track price changes and trading activity across the entire exchange.

The FMP Exchange Stock Quotes API allows users to access real-time quotes for all stocks trading on a specific exchange. This API is crucial for: Comprehensive Exchange Monitoring: Track every stock listed on a particular exchange, providing a complete view of the market activity. Real-Time Trading Data: Access up-to-date price quotes, volume, and change information for all stocks, allowing you to monitor trading trends. Portfolio Management: Compare performance across multiple stocks on the same exchange to make well-informed investment decisions. This API is ideal for investors, analysts, and traders who need an overview of trading activity and stock performance on a specific exchange.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-exchange-quote?exchange=NASDAQ`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| exchange* | string | NASDAQ |
| short | boolean | true |

**Example Response**

```json
[
  {
    "symbol": "AAACX",
    "price": 6.38,
    "change": 0,
    "volume": 0
  }
]
```

---

### Mutual Fund Price Quotes

Access real-time quotes for mutual funds with the FMP Mutual Fund Price Quotes API. Track current prices, performance changes, and key data for various mutual funds.

The FMP Mutual Fund Price Quotes API provides real-time price information and performance updates for mutual funds. Investors and analysts can use this API to: Monitor Mutual Fund Performance: Stay updated on the latest price movements and performance changes of mutual funds. Track Investment Value: Use price data to assess the value of your mutual fund investments in real-time. Analyze Trends: Compare performance across multiple mutual funds to make informed investment decisions and portfolio adjustments. This API is an essential tool for investors seeking to stay informed on mutual fund prices and performance data.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-mutualfund-quotes`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| short | boolean | true |

**Example Response**

```json
[
  {
    "symbol": "ARCFX",
    "price": 9.84,
    "change": 0.01,
    "volume": 0
  }
]
```

---

### ETF Price Quotes

Get real-time price quotes for exchange-traded funds (ETFs) with the FMP ETF Price Quotes API. Track current prices, performance changes, and key data for a wide variety of ETFs.

The FMP ETF Price Quotes API allows investors to access real-time pricing information and performance updates for ETFs. This API is essential for those looking to: Monitor ETF Performance: Stay updated on the latest prices and performance metrics of different ETFs. Evaluate Investment Opportunities: Use real-time price data to assess the value of ETFs and make informed investment decisions. Compare ETFs: Easily track and compare the performance of multiple ETFs to optimize your portfolio strategy. This API provides comprehensive information for investors and analysts looking to make data-driven decisions regarding their ETF investments.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-etf-quotes`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| short | boolean | true |

**Example Response**

```json
[
  {
    "symbol": "GULF",
    "price": 16.335,
    "change": 0.13,
    "volume": 3032
  }
]
```

---

### Full Commodities Quotes

Get up-to-the-minute quotes for commodities with the FMP Commodities Quotes API. Track the latest prices, changes, and volumes for a wide range of commodities, including oil, gold, and agricultural products.

The FMP Commodities Quotes API provides access to latest pricing information for various commodities. This API is an essential tool for: Tracking Key Commodities: Monitor real-time prices for commodities such as oil, gold, natural gas, and agricultural products. Making Timely Investment Decisions: Stay informed about price changes and volume to make well-timed trades or investments. Market Analysis: Use live data to analyze trends and fluctuations in commodity markets, helping you stay ahead of market movements. Whether you are a trader, investor, or analyst, this API delivers crucial data to keep you informed on the commodities markets.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-commodity-quotes`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| short | boolean | true |

**Example Response**

```json
[
  {
    "symbol": "DCUSD",
    "price": 19.89,
    "change": 0.23,
    "volume": 442
  }
]
```

---

### Full Cryptocurrency Quotes

Access real-time cryptocurrency quotes with the FMP Full Cryptocurrency Quotes API. Track live prices, trading volumes, and price changes for a wide range of digital assets.

The FMP Full Cryptocurrency Quotes API offers comprehensive real-time data on cryptocurrency prices, including the latest trading prices, volumes, and price fluctuations. This API is essential for: Monitoring Market Prices: Keep track of live cryptocurrency prices to make informed trading decisions. Analyzing Market Movements: Stay updated with real-time changes and volume data to identify potential opportunities in the digital asset market. Portfolio Management: Use the API to follow the performance of specific cryptocurrencies in your portfolio and adjust your strategy accordingly. This API is ideal for traders, investors, and analysts who want accurate and up-to-date information about cryptocurrency markets.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-crypto-quotes`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| short | boolean | true |

**Example Response**

```json
[
  {
    "symbol": "00USD",
    "price": 0.03071157,
    "change": -0.0026034,
    "volume": 169600
  }
]
```

---

### Full Forex Quote

Retrieve real-time quotes for multiple forex currency pairs with the FMP Batch Forex Quote API. Get real-time price changes and updates for a variety of forex pairs in a single request.

The FMP Batch Forex Quote API allows users to track real-time exchange rates for multiple currency pairs at once. This API is ideal for those who need to monitor numerous forex pairs simultaneously. Key features include: Multiple Currency Pair Tracking: Retrieve real-time quotes for several forex pairs in one request, streamlining market analysis. Comprehensive Forex Data: Access up-to-date prices, price changes, and trading volumes across a wide range of global currencies. Efficient Market Monitoring: Ideal for traders or analysts monitoring multiple currency pairs in fast-moving forex markets. The Batch Forex Quote API is a powerful tool for tracking global forex market trends and staying informed on price fluctuations for multiple pairs.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-forex-quotes`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| short | boolean | true |

**Example Response**

```json
[
  {
    "symbol": "AEDAUD",
    "price": 0.43575,
    "change": 0.0009547891,
    "volume": 344
  }
]
```

---

### Full Index Quotes

Track real-time movements of major stock market indexes with the FMP Stock Market Index Quotes API. Access live quotes for global indexes and monitor changes in their performance.

The FMP Stock Market Index Quotes API provides real-time data for various stock market indexes, offering key insights into the performance of entire markets. Features include: Live Index Data: Access up-to-the-minute quotes for major stock market indexes like the S&amp;P 500, Dow Jones, and others. Price Movement Tracking: Stay informed on index price changes and fluctuations throughout the trading day. Global Market Coverage: Follow performance for indexes across global markets, helping investors and analysts assess market sentiment and trends. This API is ideal for traders, investors, and financial professionals who need to stay updated on the movement of key stock market indexes.

**Endpoint:** `https://financialmodelingprep.com/stable/batch-index-quotes`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| short | boolean | true |

**Example Response**

```json
[
  {
    "symbol": "^DJBGIE",
    "price": 4277.52,
    "change": -15.7,
    "volume": 0
  }
]
```

---

# SecFilings

## Latest Filings

### Latest 8-K SEC Filings

Stay up-to-date with the most recent 8-K filings from publicly traded companies using the FMP Latest 8-K SEC Filings API. Get real-time access to significant company events such as mergers, acquisitions, leadership changes, and other material events that may impact the market.

The FMP Latest 8-K SEC Filings API provides timely updates on essential corporate events that are required to be disclosed to the public. These filings offer critical insights for investors and analysts, including: Real-Time Filings: Access the latest 8-K filings as they are submitted to the SEC, ensuring you stay informed of key corporate developments. Material Events: Track significant corporate events such as mergers, acquisitions, bankruptcies, changes in leadership, and more. Direct Filing Links: Get direct access to SEC filing documents, providing you with complete details and disclosures from the companies. This API is an invaluable tool for investors, analysts, and professionals who need to stay informed of market-moving corporate events.

**Endpoint:** `https://financialmodelingprep.com/stable/sec-filings-8k?from=2024-01-01&to=2024-03-01&page=0&limit=100`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| from* | string | 2024-01-01 |
| to* | string | 2024-03-01 |
| page | number | 0 |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "SUNE",
    "cik": "0000022701",
    "filingDate": "2024-03-04 00:00:00",
    "acceptedDate": "2024-03-01 22:47:48",
    "formType": "8-K",
    "hasFinancials": null,
    "link": "https://www.sec.gov/Archives/edgar/data/22701/000089710124000091/0000897101-24-000091-index.htm",
    "finalLink": "https://www.sec.gov/Archives/edgar/data/22701/000089710124000091/pegy240248_8k.htm"
  }
]
```

---

### Latest SEC Filings

Stay updated with the most recent SEC filings from publicly traded companies using the FMP Latest SEC Filings API. Access essential regulatory documents, including financial statements, annual reports, 8-K, 10-K, and 10-Q forms.

The FMP Latest SEC Filings API provides real-time access to the latest SEC filings submitted by public companies. This API is essential for investors, analysts, and compliance professionals who need to stay informed about corporate financial disclosures and material events. Key features include: Comprehensive Filing Access: Retrieve recent filings such as 8-K, 10-K, 10-Q, and other essential documents required by the SEC. Real-Time Updates: Ensure you have the latest filings as they are accepted by the SEC, helping you stay informed about any material developments in the companies you follow. Direct Filing Links: Quickly access full SEC filing documents for in-depth review and analysis of company disclosures. This API is an invaluable resource for staying up-to-date with regulatory filings and understanding the financial and operational health of public companies.

**Endpoint:** `https://financialmodelingprep.com/stable/sec-filings-financials?from=2024-01-01&to=2024-03-01&page=0&limit=100`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| from* | string | 2024-01-01 |
| to* | string | 2024-03-01 |
| page | number | 0 |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "DNN",
    "cik": "0001063259",
    "filingDate": "2024-03-01 00:00:00",
    "acceptedDate": "2024-03-01 16:52:35",
    "formType": "6-K",
    "hasFinancials": true,
    "link": "https://www.sec.gov/Archives/edgar/data/1063259/000110465924030026/0001104659-24-030026-index.htm",
    "finalLink": "https://www.sec.gov/Archives/edgar/data/1063259/000110465924030026/dnn-20231231xex99d1.htm"
  }
]
```

---

## Search Filings

### SEC Filings By Form Type

Search for specific SEC filings by form type with the FMP SEC Filings By Form Type API. Retrieve filings such as 10-K, 10-Q, 8-K, and others, filtered by the exact type of document you're looking for.

The FMP SEC Filings By Form Type API allows users to filter and retrieve SEC filings based on the document's form type. Whether you're looking for annual reports (10-K), quarterly earnings (10-Q), or event-related filings (8-K), this API provides a streamlined way to access the exact forms needed for analysis or compliance: Targeted Filings Search: Search for SEC filings by form type to retrieve specific reports such as 8-K, 10-K, 10-Q, and more. Direct Links to Documents: Access the full filing and any associated exhibits directly from the SEC, ensuring complete visibility into company disclosures. Regulatory Compliance Monitoring: Use this API to monitor filings related to compliance events, mergers, acquisitions, financial disclosures, and governance updates. This API is an essential tool for investors, analysts, and regulatory professionals who need quick access to specific types of filings for compliance, analysis, or investment decisions.

**Endpoint:** `https://financialmodelingprep.com/stable/sec-filings-search/form-type?formType=8-K&from=2024-01-01&to=2024-03-01&page=0&limit=100`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| formType* | string | 8-K |
| from* | string | 2024-01-01 |
| to* | string | 2024-03-01 |
| page | number | 0 |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "SUNE",
    "cik": "0000022701",
    "filingDate": "2024-03-04 00:00:00",
    "acceptedDate": "2024-03-01 22:47:48",
    "formType": "8-K",
    "link": "https://www.sec.gov/Archives/edgar/data/22701/000089710124000091/0000897101-24-000091-index.htm",
    "finalLink": "https://www.sec.gov/Archives/edgar/data/22701/000089710124000091/pegy240248_8k.htm"
  }
]
```

---

### SEC Filings By Symbol

Search and retrieve SEC filings by company symbol using the FMP SEC Filings By Symbol API. Gain direct access to regulatory filings such as 8-K, 10-K, and 10-Q reports for publicly traded companies.

The FMP SEC Filings By Symbol API allows users to search for and retrieve SEC filings based on a specific company's stock symbol. This API provides crucial regulatory documents that are essential for compliance monitoring, financial analysis, and investment research: Company-Specific Filings: Access detailed SEC filings for any publicly traded company by simply entering its stock symbol. Direct Document Links: Receive direct links to the full SEC filings and related exhibits, ensuring full transparency for your research. Real-Time Data Updates: The API provides real-time updates, giving you access to the most recent filings as soon as they are made available by the SEC. This API is invaluable for investors, analysts, and compliance officers who need to monitor and review regulatory filings tied to a specific company.

**Endpoint:** `https://financialmodelingprep.com/stable/sec-filings-search/symbol?symbol=AAPL&from=2024-01-01&to=2024-03-01&page=0&limit=100`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| from* | string | 2024-01-01 |
| to* | string | 2024-03-01 |
| page | number | 0 |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "cik": "0000320193",
    "filingDate": "2024-03-01 00:00:00",
    "acceptedDate": "2024-03-01 18:36:45",
    "formType": "4",
    "link": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000039/0000320193-24-000039-index.htm",
    "finalLink": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000039/xslF345X05/wk-form4_1709336196.xml"
  }
]
```

---

### SEC Filings By CIK

Search for SEC filings using the FMP SEC Filings By CIK API. Access detailed regulatory filings by Central Index Key (CIK) number, enabling you to track all filings related to a specific company or entity.

The FMP SEC Filings By CIK API allows users to retrieve SEC filings by the Central Index Key (CIK) number, providing comprehensive access to a company or entity's official filings. This API is designed for: Entity-Specific Filings: Search for SEC filings linked to a specific CIK number, which uniquely identifies publicly traded companies, mutual funds, and other registrants. Real-Time Filings: Receive updates on the latest SEC submissions for the entity, including 8-K, 10-K, and 10-Q forms, among others. Direct Links to Filings: Access direct links to the official SEC filings and any associated documents or exhibits. This API is ideal for financial analysts, investors, and compliance officers who require precise and up-to-date filings based on CIK identifiers.

**Endpoint:** `https://financialmodelingprep.com/stable/sec-filings-search/cik?cik=0000320193&from=2024-01-01&to=2024-03-01&page=0&limit=100`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| cik* | string | 0000320193 |
| from* | string | 2024-01-01 |
| to* | string | 2024-03-01 |
| page | number | 0 |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "cik": "0000320193",
    "filingDate": "2024-03-01 00:00:00",
    "acceptedDate": "2024-03-01 18:36:45",
    "formType": "4",
    "link": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000039/0000320193-24-000039-index.htm",
    "finalLink": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000039/xslF345X05/wk-form4_1709336196.xml"
  }
]
```

---

### SEC Filings By Name

Search for SEC filings by company or entity name using the FMP SEC Filings By Name API. Quickly retrieve official filings for any organization based on its name.

The FMP SEC Filings By Name API enables users to search for SEC filings using a company or entity name, providing access to detailed regulatory filings. This API is essential for: Entity-Specific Search: Find SEC filings for companies, mutual funds, and other entities by searching their name. Comprehensive Filing Access: Get access to key filings such as 8-K, 10-K, 10-Q forms, and more, with the ability to view specific company filings. Company Information: Along with SEC filings, receive additional details such as CIK number, business address, and contact information. This API is ideal for investors, financial analysts, and regulatory compliance officers who need to locate filings based on company or entity names.

**Endpoint:** `https://financialmodelingprep.com/stable/sec-filings-company-search/name?company=Berkshire`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| company* | string | Berkshire |

**Example Response**

```json
[
  {
    "symbol": "BGRY",
    "name": "BERKSHIRE GREY, INC.",
    "cik": "0001824734",
    "sicCode": "3569",
    "industryTitle": "GENERAL INDUSTRIAL MACHINERY & EQUIPMENT, NEC",
    "businessAddress": "140 SOUTH ROAD, BEDFORD MA 01730",
    "phoneNumber": "(833) 848-9900"
  }
]
```

---

## Company Info

### SEC Filings Company Search By Symbol

Find company information and regulatory filings using a stock symbol with the FMP SEC Filings Company Search By Symbol API. Quickly access essential company details based on stock ticker symbols.

The FMP SEC Filings Company Search By Symbol API allows users to search for a company's SEC filings by simply entering its stock symbol. This API provides valuable information such as: Stock Symbol-Based Search: Enter a company&rsquo;s ticker symbol to find official SEC filings and corporate details. Detailed Company Information: Retrieve the company&rsquo;s name, CIK number, industry classification (SIC code), and business address. Filing Access: Access crucial SEC filings, enabling comprehensive regulatory research and corporate event tracking. This API is perfect for investors, financial analysts, and compliance professionals who need to quickly pull company-specific SEC filings and information using a stock symbol.

**Endpoint:** `https://financialmodelingprep.com/stable/sec-filings-company-search/symbol?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "name": "APPLE INC.",
    "cik": "0000320193",
    "sicCode": "3571",
    "industryTitle": "ELECTRONIC COMPUTERS",
    "businessAddress": "ONE APPLE PARK WAY, CUPERTINO CA 95014",
    "phoneNumber": "(408) 996-1010"
  }
]
```

---

### SEC Filings Company Search By CIK

Easily find company information using a CIK (Central Index Key) with the FMP SEC Filings Company Search By CIK API. Access essential company details and filings linked to a specific CIK number.

The FMP SEC Filings Company Search By CIK API enables users to search for a company&rsquo;s regulatory filings and corporate information based on its unique Central Index Key (CIK). This API is ideal for: CIK-Based Search: Input a company&rsquo;s CIK number to retrieve corporate data and access its SEC filings. Comprehensive Company Information: Retrieve details such as company name, CIK number, SIC code, business address, and phone number. Access to SEC Filings: Instantly access the latest SEC filings for companies, allowing for thorough financial research and corporate tracking. This API is particularly useful for investors, analysts, and compliance professionals who need to gather detailed company information and filing history using a CIK number.

**Endpoint:** `https://financialmodelingprep.com/stable/sec-filings-company-search/cik?cik=0000320193`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| cik* | string | 0000320193 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "name": "APPLE INC.",
    "cik": "0000320193",
    "sicCode": "3571",
    "industryTitle": "ELECTRONIC COMPUTERS",
    "businessAddress": "ONE APPLE PARK WAY, CUPERTINO CA 95014",
    "phoneNumber": "(408) 996-1010"
  }
]
```

---

### SEC Company Full Profile

Retrieve detailed company profiles, including business descriptions, executive details, contact information, and financial data with the FMP SEC Company Full Profile API.

The FMP SEC Company Full Profile API offers comprehensive data on companies registered with the SEC. This API is ideal for: Detailed Company Profiles: Access in-depth information on a company's operations, SIC code, CEO, fiscal year, and employee count. Executive and Contact Information: Retrieve key executive details and contact information, including business and mailing addresses, phone numbers, and website links. Company Description and Operations: Get a detailed company description, including its products, services, markets, and business sectors, allowing for a full understanding of its operations. Financial and Regulatory Data: This API provides essential financial data like fiscal year end, IPO date, and links to SEC filings. This API is crucial for investors, analysts, and researchers who need detailed corporate profiles for financial analysis, competitive research, and investment decision-making.

**Endpoint:** `https://financialmodelingprep.com/stable/sec-profile?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| cik-A | string | 320193 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "cik": "0000320193",
    "registrantName": "Apple Inc.",
    "sicCode": "3571",
    "sicDescription": "Electronic Computers",
    "sicGroup": "Consumer Electronics",
    "isin": "US0378331005",
    "businessAddress": "ONE APPLE PARK WAY,CUPERTINO CA 95014,(408) 996-1010",
    "mailingAddress": "ONE APPLE PARK WAY,CUPERTINO CA 95014",
    "phoneNumber": "(408) 996-1010",
    "postalCode": "95014",
    "city": "Cupertino",
    "state": "CA",
    "country": "US",
    "description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide. The company offers iPhone, a line of smartphones; Mac, a line of personal computers; iPad, a line of multi-purpose tablets; and wearables, home, and accessories comprising AirPods, Apple TV, Apple Watch, Beats products, and HomePod. It also provides AppleCare support and cloud services; and operates various platforms, including the App Store that allow customers to discov...",
    "ceo": "Timothy D. Cook",
    "website": "https://www.apple.com",
    "exchange": "NASDAQ",
    "stateLocation": "CA",
    "stateOfIncorporation": "CA",
    "fiscalYearEnd": "09-30",
    "ipoDate": "1980-12-12",
    "employees": "164000",
    "secFilingsUrl": "https://www.sec.gov/cgi-bin/browse-edgar?CIK=0000320193",
    "taxIdentificationNumber": "94-2404110",
    "fiftyTwoWeekRange": "195.07 - 316.94",
    "isActive": true,
    "assetType": "stock",
    "openFigiComposite": "BBG000B9XRY4",
    "priceCurrency": "USD",
    "marketSector": "Technology",
    "securityType": null,
    "isEtf": false,
    "isAdr": false,
    "isFund": false
  }
]
```

---

## Industry Classification

### Industry Classification List

Retrieve a comprehensive list of industry classifications, including Standard Industrial Classification (SIC) codes and industry titles with the FMP Industry Classification List API.

The FMP Industry Classification List API provides a complete directory of SIC codes and corresponding industry titles. This API is essential for: Industry Research: Access an organized list of industries with SIC codes, allowing users to categorize companies based on their industry sector. Company Classification: Retrieve SIC codes for industries ranging from manufacturing to services, helping users classify and analyze companies by their primary business activities. Standardized Data: Ensure consistency when researching or classifying companies, as this API provides standardized SIC codes and official industry titles. This API is ideal for analysts, researchers, and businesses looking to categorize companies based on industry standards.

**Endpoint:** `https://financialmodelingprep.com/stable/standard-industrial-classification-list`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| industryTitle | string | SERVICES |
| sicCode | string | 7371 |

**Example Response**

```json
[
  {
    "office": "Office of Life Sciences",
    "sicCode": "100",
    "industryTitle": "AGRICULTURAL PRODUCTION-CROPS"
  }
]
```

---

### Industry Classification Search

Search and retrieve industry classification details for companies, including SIC codes, industry titles, and business information, with the FMP Industry Classification Search API.

The FMP Industry Classification Search API allows users to search for company information based on their Standard Industrial Classification (SIC) codes. This API provides: Company Lookup by Industry: Search for companies by industry classifications, retrieving details such as SIC codes, industry titles, and company contact information. Business Information Access: Get comprehensive company information, including business addresses and phone numbers, making it easier to identify and classify businesses by their industry. SIC Code Matching: Use this API to match companies with their corresponding industry sectors, enhancing your ability to perform industry-specific research and classification. This API is valuable for businesses, investors, and researchers who need detailed company information tied to specific industry sectors.

**Endpoint:** `https://financialmodelingprep.com/stable/industry-classification-search`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol | string | AAPL |
| cik | string | 320193 |
| sicCode | string | 7371 |

**Example Response**

```json
[
  {}
]
```

---

### All Industry Classification

Access comprehensive industry classification data for companies across all sectors with the FMP All Industry Classification API. Retrieve key details such as SIC codes, industry titles, and business contact information.

The FMP All Industry Classification API provides a complete overview of companies classified by industry sector. Users can retrieve: Full Industry Classification Data: Access detailed information on companies, including SIC codes, industry titles, and business addresses, for all available industries. Comprehensive Company Information: Get relevant details such as company names, CIK numbers, SIC codes, phone numbers, and addresses, helping you identify and analyze businesses across various industries. Cross-Industry Analysis: Use this API to study companies within specific industries or across multiple sectors for a complete industry overview. This API is ideal for investors, analysts, and market researchers looking for extensive industry classification and business data.

**Endpoint:** `https://financialmodelingprep.com/stable/all-industry-classification`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| page | number | 0 |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "0Q16.L",
    "name": "BANK OF AMERICA CORP /DE/",
    "cik": "0000070858",
    "sicCode": "6021",
    "industryTitle": "NATIONAL COMMERCIAL BANKS",
    "businessAddress": "['BANK OF AMERICA CORPORATE CENTER', 'CHARLOTTE NC 28255']",
    "phoneNumber": "7043868486"
  }
]
```

---

# EarningsTranscript

## Earnings Transcript

### Latest Earning Transcripts

Access available earnings transcripts for companies with the FMP Latest Earning Transcripts API. Retrieve a list of companies with earnings transcripts, along with the total number of transcripts available for each company.

The FMP Latest Earning Transcripts API provides users with essential data on the availability of earnings transcripts for various companies. This API is ideal for financial analysts, investors, and researchers looking to track earnings performance over time. Identify Available Transcripts: Quickly access a list of companies with earnings transcripts, complete with the number of available transcripts for each. Support Earnings Analysis: Use the transcript count to further analyze earnings call data and gain insights into company performance. Track Historical Data: Discover companies with multiple transcripts to track earnings calls over different quarters or years. Example Use Case An investor looking to analyze a company&rsquo;s earnings performance over several quarters can use the Earnings Transcript List API to identify companies with multiple earnings call transcripts and retrieve the necessary documents for deeper financial analysis.

**Endpoint:** `https://financialmodelingprep.com/stable/earning-call-transcript-latest`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| limit | number | 100 |
| page | number | 0 |

**Example Response**

```json
[
  {
    "symbol": "GASS",
    "period": "Q1",
    "fiscalYear": 2026,
    "date": "2026-06-05"
  }
]
```

---

### Earnings Transcript

Access the full transcript of a company’s earnings call with the FMP Earnings Transcript API. Stay informed about a company’s financial performance, future plans, and overall strategy by analyzing management's communication.

The FMP Earnings Transcript API provides complete access to the text transcript of a company&rsquo;s earnings call. This API is essential for: In-Depth Financial Analysis: Gain valuable insights into a company&rsquo;s financial performance by reviewing what executives say during earnings calls. The transcript can provide context and details beyond what&rsquo;s available in standard financial reports. Strategic Planning: Learn about a company&rsquo;s future plans and strategic direction straight from management. Understanding the company&rsquo;s priorities and challenges can help investors make informed decisions. Risk Identification: Use the transcript to identify any potential red flags or areas of concern that might not be immediately apparent in the earnings report. This can include management's tone, response to analysts' questions, or any mention of operational or financial difficulties. Example Use Case Investor Insight: An investor might use the Earnings Transcript API to review the most recent earnings call for a retail company. By analyzing the transcript, the investor can assess the company&rsquo;s response to market trends, management&rsquo;s outlook on upcoming quarters, and any potential risks that were discussed.

**Endpoint:** `https://financialmodelingprep.com/stable/earning-call-transcript?symbol=AAPL&year=2020&quarter=3`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| year* | string | 2020 |
| quarter* | string | 3 |
| limit | number | 1 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "period": "Q3",
    "year": 2020,
    "date": "2020-07-30",
    "content": "Operator: Good day, everyone. Welcome to the Apple Incorporated Third Quarter Fiscal Year 2020 Earnings Conference Call. Today's call is being recorded. At this time, for opening remarks and introductions, I would like to turn things over to Mr. Tejas Gala, Senior Manager, Corporate Finance and Investor Relations. Please go ahead, sir.\nTejas Gala: Thank you. Good afternoon and thank you for joining us. Speaking first today is Apple's CEO, Tim Cook; and he'll be followed by CFO, Luca Maestri. Aft..."
  }
]
```

---

### Transcripts Dates By Symbol

Access earnings call transcript dates for specific companies with the FMP Transcripts Dates By Symbol API. Get a comprehensive overview of earnings call schedules based on fiscal year and quarter.

The FMP Transcripts Dates By Symbol API provides users with precise information about when earnings call transcripts are available for a given company. This API is ideal for investors, analysts, and researchers who want to track earnings discussions and financial insights over time, including: Earnings Call Availability by Quarter: Retrieve transcript dates by quarter and fiscal year to track a company's performance. Timely Access to Transcripts: Get access to transcripts for upcoming or historical earnings calls for in-depth analysis. Comprehensive Coverage: Identify and analyze earnings call transcripts across multiple quarters for better decision-making. This API is designed to help users stay informed about earnings call schedules and access key financial insights through transcripts from specific periods. Example Use Case An investment firm can use the Transcripts Dates By Symbol API to keep track of a company's earnings calls for each quarter and access these transcripts for detailed performance analysis and strategic planning.

**Endpoint:** `https://financialmodelingprep.com/stable/earning-call-transcript-dates?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |

**Example Response**

```json
[
  {
    "quarter": 2,
    "fiscalYear": 2026,
    "date": "2026-04-30"
  }
]
```

---

### Available Transcript Symbols

Access a complete list of stock symbols with available earnings call transcripts using the FMP Available Earnings Transcript Symbols API. Retrieve information on which companies have earnings transcripts and how many are accessible for detailed financial analysis.

The FMP Available Earnings Transcript Symbols API provides users with a comprehensive list of companies that have earnings call transcripts available. This API is designed for analysts, investors, and researchers who want to track corporate earnings discussions and performance over time, including: Earnings Transcript Availability: Get a list of companies with earnings call transcripts available for review. Number of Available Transcripts: View the total number of transcripts available for each company, allowing users to analyze trends across multiple periods. Quick Access to Relevant Symbols: Easily identify which companies provide insights through earnings calls, facilitating research and performance analysis. This API simplifies the process of discovering which companies have earnings transcripts, making it easier to access and analyze financial discussions. Example Use Case A research analyst can use the Available Earnings Transcript Symbols API to compile a list of companies with multiple earnings transcripts, allowing them to focus on companies with the most available historical data for better trend analysis.

**Endpoint:** `https://financialmodelingprep.com/stable/earnings-transcript-list`

**Example Response**

```json
[
  {
    "symbol": "INBS",
    "companyName": "Intelligent Bio Solutions Inc.",
    "noOfTranscripts": "6"
  }
]
```

---

# Senate

## Latest

### Latest Senate Financial Disclosures

Access the latest financial disclosures from U.S. Senate members with the FMP Latest Senate Financial Disclosures API. Track recent trades, asset ownership, and transaction details for enhanced transparency in government financial activities.

The FMP Latest Senate Financial Disclosures API provides up-to-date information on trades and asset ownership by U.S. Senate members. With this API, users can: Monitor Senate Member Transactions: Access real-time disclosures detailing trades, sales, and purchases made by U.S. Senate members and their families. Detailed Transaction Data: Retrieve transaction details, including asset types (stocks, bonds, real estate), transaction dates, amounts, and ownership types. Stay Informed: Follow recent disclosures to stay informed about financial activity by key political figures. This API is essential for those who want to track political figures' financial activities and understand their investment behaviors.

**Endpoint:** `https://financialmodelingprep.com/stable/senate-latest?page=0&limit=100`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| page | number | 0 |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "CSX",
    "senateID": "T000278",
    "disclosureDate": "2026-07-16",
    "transactionDate": "2026-06-08",
    "firstName": "Tommy",
    "lastName": "Tuberville",
    "office": "Tommy Tuberville",
    "district": "AL",
    "owner": "Joint",
    "assetDescription": "CSX Corp",
    "assetType": "Stock",
    "type": "Sale",
    "amount": "$15,001 - $50,000",
    "comment": "",
    "link": "https://efdsearch.senate.gov/search/view/ptr/392ac3e5-07f6-4f8c-840f-84e9066ffb29/"
  }
]
```

---

### Latest House Financial Disclosures

Access real-time financial disclosures from U.S. House members with the FMP Latest House Financial Disclosures API. Track recent trades, asset ownership, and financial holdings for enhanced visibility into political figures' financial activities.

The FMP Latest House Financial Disclosures API provides up-to-date information on trades, sales, and financial assets held by members of the U.S. House of Representatives. This API allows users to: Monitor House Member Transactions: Access recent financial disclosures that detail the transactions and asset ownership of U.S. House members and their families. Comprehensive Transaction Data: View detailed information, including asset types, transaction amounts, dates, and whether capital gains were reported. Stay Informed: Gain insights into the investment activities of elected officials and track any changes in their holdings. This API is ideal for users who seek transparency and accountability in the financial dealings of government representatives.

**Endpoint:** `https://financialmodelingprep.com/stable/house-latest?page=0&limit=100`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| page | number | 0 |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "HLT",
    "senateID": "J000309",
    "disclosureDate": "2026-07-16",
    "transactionDate": "2026-06-15",
    "firstName": "Jonathan",
    "lastName": "Jackson",
    "office": "Jonathan Jackson",
    "district": "IL01",
    "owner": "Spouse",
    "assetDescription": "Hilton Worldwide Holdings Inc",
    "assetType": "Stock",
    "type": "Purchase",
    "amount": "$1,001 - $15,000",
    "capitalGainsOver200USD": "False",
    "comment": "",
    "link": "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20034908.pdf"
  }
]
```

---

## Symbol

### Senate Trading Activity

Monitor the trading activity of US Senators with the FMP Senate Trading Activity API. Access detailed information on trades made by Senators, including trade dates, assets, amounts, and potential conflicts of interest.

The FMP Senate Trading Activity API provides comprehensive data on the trading activities of US Senators, as required by the STOCK Act of 2012. This API is essential for: Transparency &amp; Accountability: Access a detailed list of trades made by US Senators, including the date, asset, amount traded, and price per share. This transparency helps ensure accountability and provides insights into the financial activities of elected officials. Conflict of Interest Identification: Use the data to identify potential conflicts of interest by analyzing trades made by Senators in companies or sectors where they may have legislative influence. This information is crucial for investors who want to ensure ethical investment practices. Informed Investment Decisions: Investors can track the trading activities of Senators to gain insights into market trends or to flag any trades that might indicate a significant market move. Knowing when and what Senators are trading can provide a unique perspective on market sentiment. This API is a powerful tool for investors, analysts, and anyone interested in monitoring the financial activities of US Senators and ensuring transparency in government. Example Use Case Ethical Investing: An investor focused on ethical investing might use the Senate Trading Activity API to avoid investing in companies where Senators have made trades, especially if those trades could be seen as conflicts of interest. By doing so, the investor aligns their portfolio with ethical standards.

**Endpoint:** `https://financialmodelingprep.com/stable/senate-trades?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| page | number | 0 |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "senateID": "W000802",
    "disclosureDate": "2026-07-08",
    "transactionDate": "2026-06-24",
    "firstName": "Sheldon",
    "lastName": "Whitehouse",
    "office": "Sheldon Whitehouse",
    "district": "RI",
    "owner": "Spouse",
    "assetDescription": "Apple Inc",
    "assetType": "Stock",
    "type": "Sale",
    "amount": "$15,001 - $50,000",
    "capitalGainsOver200USD": "False",
    "comment": "",
    "link": "https://efdsearch.senate.gov/search/view/ptr/5d9b1b8e-2ae1-442b-860c-e79b8a701dc6/"
  }
]
```

---

### Senate Trades By Name

Search U.S. Senate stock trades by the member's name.

**Endpoint:** `https://financialmodelingprep.com/stable/senate-trades-by-name?name=Jerry`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| name* | string | Jerry |

**Example Response**

```json
[
  {
    "symbol": "",
    "senateID": "M000934",
    "disclosureDate": "2026-06-25",
    "transactionDate": "2026-05-27",
    "firstName": "Jerry",
    "lastName": "Moran",
    "office": "Jerry Moran",
    "district": "KS",
    "owner": "Spouse",
    "assetDescription": "Berkshire Hathaway Inc (1)",
    "assetType": "Stock",
    "type": "Purchase",
    "amount": "$1,001 - $15,000",
    "capitalGainsOver200USD": "False",
    "comment": "",
    "link": "https://efdsearch.senate.gov/search/view/ptr/7caf1b69-3678-4420-8812-a1476a1a6158/"
  }
]
```

---

### Senate Trades By ID

Look up U.S. Senate stock trades by a member's Senate ID.

**Endpoint:** `https://financialmodelingprep.com/stable/senate-trades-by-id`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| page | number | 0 |
| limit | number | 100 |
| senateID | string | S000033 |

**Example Response**

```json
[
  {
    "symbol": "MA",
    "senateID": "T000278",
    "disclosureDate": "2026-07-16",
    "transactionDate": "2026-06-08",
    "firstName": "Tommy",
    "lastName": "Tuberville",
    "office": "Tommy Tuberville",
    "district": "AL",
    "owner": "Joint",
    "assetDescription": "Mastercard Inc",
    "assetType": "Stock",
    "type": "Sale",
    "amount": "$15,001 - $50,000",
    "capitalGainsOver200USD": "False",
    "comment": "",
    "link": "https://efdsearch.senate.gov/search/view/ptr/392ac3e5-07f6-4f8c-840f-84e9066ffb29/"
  }
]
```

---

### U.S. House Trades

Track the financial trades made by U.S. House members and their families with the FMP U.S. House Trades API. Access real-time information on stock sales, purchases, and other investment activities to gain insight into their financial decisions.

The FMP U.S. House Trades API provides a comprehensive view of the trading activities of U.S. House members and their spouses. This API offers detailed data on trades, including stock sales and purchases, ownership details, and transaction amounts. Users can: Monitor Trading Activity: Stay informed about the latest stock trades made by U.S. House members and their families. Understand Financial Moves: Gain insights into the financial decisions of government officials through detailed trade data. Transparency and Accountability: Use the data to follow the financial actions of U.S. House members, ensuring greater transparency in government. This API is ideal for political analysts, journalists, and the general public interested in understanding the financial moves of U.S. House representatives.

**Endpoint:** `https://financialmodelingprep.com/stable/house-trades?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| page | number | 0 |
| limit | number | 100 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "senateID": "K000389",
    "disclosureDate": "2026-07-08",
    "transactionDate": "2026-06-05",
    "firstName": "Ro",
    "lastName": "Khanna",
    "office": "Ro Khanna",
    "district": "CA17",
    "owner": "",
    "assetDescription": "Apple Inc",
    "assetType": "Stock Option",
    "type": "Purchase",
    "amount": "$1,001 - $15,000",
    "capitalGainsOver200USD": "False",
    "comment": "",
    "link": "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/9116206.pdf"
  }
]
```

---

### House Trades By Name

Search U.S. House stock trades by the member's name.

**Endpoint:** `https://financialmodelingprep.com/stable/house-trades-by-name?name=James`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| name* | string | James |

**Example Response**

```json
[
  {
    "symbol": "SOLV",
    "senateID": "H001072",
    "disclosureDate": "2026-01-23",
    "transactionDate": "2025-12-31",
    "firstName": "James French",
    "lastName": "Hill",
    "office": "James French Hill",
    "district": "AR02",
    "owner": "",
    "assetDescription": "Solventum Corporation Common Stock",
    "assetType": "Stock",
    "type": "Sale (Full)",
    "amount": "$15,001 - $50,000",
    "capitalGainsOver200USD": "False",
    "comment": "",
    "link": "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20033661.pdf"
  }
]
```

---

### House Trades By ID

Look up U.S. House stock trades by a member's ID.

**Endpoint:** `https://financialmodelingprep.com/stable/house-trades-by-id`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| page | number | 0 |
| limit | number | 100 |
| senateID | string | P000197 |

**Example Response**

```json
[
  {
    "symbol": "INTU",
    "senateID": "A000372",
    "disclosureDate": "2026-07-16",
    "transactionDate": "2026-06-10",
    "firstName": "Richard W.",
    "lastName": "Allen",
    "office": "Richard W. Allen",
    "district": "GA12",
    "owner": "Spouse",
    "assetDescription": "Intuit Inc",
    "assetType": "Stock",
    "type": "Sale",
    "amount": "$15,001 - $50,000",
    "capitalGainsOver200USD": "False",
    "comment": "",
    "link": "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20034945.pdf"
  }
]
```

---

## Profile

### Senate Profiles

Profile details for members of Congress: party, state, position, and years active.

**Endpoint:** `https://financialmodelingprep.com/stable/senate-profile`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| active | boolean | true |
| senateID | string | P000197 |
| latestParty | string | Republican |
| latestPosition | string | Representative |
| page | number | 0 |
| limit | number | 500 |

**Example Response**

```json
[
  {
    "senateID": "L000397",
    "firstName": "Zoe",
    "lastName": "Lofgren",
    "birthDate": "1947-12-20",
    "latestParty": "Democrat",
    "latestState": "CA",
    "latestPosition": "Representative",
    "image": "https://images.financialmodelingprep.com/senate/L000397.jpg",
    "active": true,
    "yearsActive": 31.5
  }
]
```

---

### Senate Positions

Congressional positions a member has held, with term dates, party, and state.

**Endpoint:** `https://financialmodelingprep.com/stable/senate-positions`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| senateID | string | P000197 |
| party | string | Republican |
| position | string | Representative |
| page | number | 0 |
| limit | number | 300 |

**Example Response**

```json
[
  {
    "senateID": "Z000018",
    "congressNumber": 119,
    "startDate": "2025-01-02",
    "endDate": null,
    "party": "Republican",
    "position": "Representative",
    "state": "MT",
    "yearsInTerm": 0.7
  }
]
```

---

### Senate Net Worth

Itemized net-worth disclosures for a member: assets, liabilities, and income by filing year.

**Endpoint:** `https://financialmodelingprep.com/stable/senate-net-worth?senateID=P000197&page=0&limit=250`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| senateID* | string | P000197 |

**Example Response**

```json
[
  {
    "senateID": "P000197",
    "formType": "House Report",
    "year": 2022,
    "filingDate": "2023-05-15",
    "section": "Liabilities",
    "category": "Mortgage & Real Estate Liability",
    "name": "Union Bank of California",
    "assetType": "Mortgage on 2640 Broadway, San Francisco, CA",
    "incomeType": null,
    "owner": "Joint",
    "comment": null,
    "debtDetails": {
      "dateIncurred": "September 2007"
    },
    "valueRange": {
      "min": 1000001,
      "max": 5000000
    },
    "value": 3000001,
    "incomeRange": null,
    "income": null,
    "link": "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2022/10053231.pdf"
  }
]
```

---

### Senate Net Worth Aggregated

Aggregated net-worth totals for a member by year, grouped by asset and liability type.

**Endpoint:** `https://financialmodelingprep.com/stable/senate-net-worth-aggregated?senateID=P000197`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| senateID* | string | P000197 |
| totalsCol | string |  |

**Example Response**

```json
[
  {
    "senateID": "P000197",
    "year": 2024,
    "total": 225219551,
    "realEstateLiabilities": 27000005,
    "cashAndCashEquivalents": 291009,
    "businessAndSelfEmployment": 0,
    "realEstate": 45032504,
    "ownershipInterest": 70140014,
    "stock": 136748525,
    "options": 0,
    "revolvingAndCreditLines": 1500002,
    "assetBackedSecurities": 4475006,
    "businessLiabilities": 3000001,
    "mutualFundsAndETFs": 32501
  }
]
```

---

# Websockets

## Websocket

### Standard WebSocket

Authenticate your WebSocket session on wss://socket.financialmodelingprep.com by sending your API key in a login event 
<p>If your API key is valid, you will start receiving data confirming your session is active. If it's invalid, you will receive an appropriate error message.

**Endpoint:** `wss://socket.financialmodelingprep.com`

**Example Response**

```json
{
  "event": "login",
  "data": {
    "status": 200,
    "message": "Authenticated"
  }
}
```

---

### Quote Subscription

Subscribe to live price updates for one or multiple tickers via WebSocket. By default, based on the subscription tier you will be permitted to stream quote information limited to your plan. In order to receive "live" quotes, you must fill out the user declaration form. The symbols allowed for the stream are determined when the stream connection is established. If you would like to change the symbol sets, please unsubscribe and subscribe again with the updated symbol sets.

**Parameters**

| Field | Type | Example |
| --- | --- | --- |
| event* | string | "subscribe" |
| tickers* | string \| array | "AAPL" or ["AAPL", "MSFT", "^GSPC"] |

**Example Response**

```json
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "price": 239.62,
  "changesPercentage": 1.23363,
  "change": 2.92,
  "dayLow": 236.3235,
  "dayHigh": 241.22,
  "yearHigh": 260.1,
  "yearLow": 169.21,
  "marketCap": 3556056617328.9995,
  "priceAvg50": 221.5888,
  "priceAvg200": 221.55185,
  "exchange": "NASDAQ",
  "volume": 20490499,
  "avgVolume": 56040420.3,
  "open": 237.175,
  "previousClose": 236.7,
  "eps": 7.26,
  "pe": 33.01,
  "earningsAnnouncement": "2025-10-30T20:00:00.000+0000",
  "sharesOutstanding": 14840399872,
  "timestamp": 1758032977
}
```

---

### Market Stream Subscription

Subscribe to real-time exchange streams, FMP synthetic streams, or delayed streams. This feed is only available to users who have completed their user declaration form and have been approved for direct streaming services. For more information, please contact marketdata@financialmodelingprep.com

**Parameters**

| Field | Type | Example |
| --- | --- | --- |
| event* | string | "subscribe" |
| stream* | string | Exchange:  "nasdaq-basic-w-nls-plus", "iex-tops", "tsx-level-1", "tsxv-level-1", "lse-level-1", "cboe-index-main" \| FMP:  "fmp-crypto-stream", "fmp-index-stream", "fmp-commodity-stream", "fmp-currency-stream", "fmp-us-equities-stream", "fmp-us-otc-stream", "fmp-uk-equities-stream", "fmp-ca-equities-stream" \| Delayed: Add "-delayed" suffix to any stream |

**Example Response**

```json
{
  "symbol": "XKMYA.IS",
  "name": "BIST Kimya Petrol Plastik",
  "price": 13057.45,
  "changesPercentage": 0.35246,
  "change": 45.86,
  "dayLow": 13031.22,
  "dayHigh": 13085.88,
  "yearHigh": 13085.88,
  "yearLow": 13011.59,
  "marketCap": 0,
  "priceAvg50": 13245.1474,
  "priceAvg200": 11936.814,
  "exchange": "INDEX",
  "volume": 0,
  "avgVolume": 0,
  "open": 13051.14,
  "previousClose": 13011.59,
  "eps": null,
  "pe": null,
  "earningsAnnouncement": null,
  "sharesOutstanding": null,
  "timestamp": 1766045220,
  "range": "13011.59 - 13085.88",
  "type": "index",
  "updatedAt": "2025-12-18T08:22:00.504Z"
}
```

---

### Unsubscribe Ticker

Stop receiving updates for a particular ticker.

**Parameters**

| Field | Type | Example |
| --- | --- | --- |
| event* | string | "unsubscribe" |
| ticker* | string \| array | "AAPL" or ["AAPL", "MSFT", "^GSPC"] |

---

### Unsubscribe Market Stream

Stop receiving aggregated data from a stream.

**Parameters**

| Field | Type | Example |
| --- | --- | --- |
| event* | string | "unsubscribe" |
| stream* | string | Stream identifier to unsubscribe from |

**Example Response**

```json
{
  "event": "unsubscribe",
  "status": 200,
  "message": "Unsubscribed from fmp-index-stream stream."
}
```

---

### Heartbeat Event

WebSocket server sends regular heartbeat events to signal active connection. 
 No action is required upon receiving this event. Use it to monitor connection health and auto-reconnect if missed.

**Example Response**

```json
{
  "event": "heartbeat",
  "timestamp": 1747473420002
}
```

---

## Socket.io

### Socket.io WebSocket

Authenticate your WebSocket session on wss://socketio.financialmodelingprep.com using Socket.IO protocol with your API key. If your API key is valid, you will start receiving data confirming your session is active. If it's invalid, you will receive an appropriate error message.

**Endpoint:** `wss://socketio.financialmodelingprep.com`

**Example Response**

```json
{
  "event": "login",
  "data": {
    "status": 200,
    "message": "Authenticated"
  }
}
```

---

### Quote Subscription

Subscribe to live price updates for one or multiple tickers via Socket.IO. By default, based on the subscription tier you will be permitted to stream quote information limited to your plan. In order to receive "live" quotes, you must fill out the user declaration form. The symbols allowed for the stream are determined when the stream connection is established. If you would like to change the symbol sets, please unsubscribe and subscribe again with the updated symbol sets.

**Parameters**

| Field | Type | Example |
| --- | --- | --- |
| tickers* | string \| array | "AAPL" or ["AAPL", "MSFT", "^GSPC"] |

**Example Response**

```json
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "price": 239.62,
  "changesPercentage": 1.23363,
  "change": 2.92,
  "dayLow": 236.3235,
  "dayHigh": 241.22,
  "yearHigh": 260.1,
  "yearLow": 169.21,
  "marketCap": 3556056617328.9995,
  "priceAvg50": 221.5888,
  "priceAvg200": 221.55185,
  "exchange": "NASDAQ",
  "volume": 20490499,
  "avgVolume": 56040420.3,
  "open": 237.175,
  "previousClose": 236.7,
  "eps": 7.26,
  "pe": 33.01,
  "earningsAnnouncement": "2025-10-30T20:00:00.000+0000",
  "sharesOutstanding": 14840399872,
  "timestamp": 1758032977
}
```

---

### Market Stream Subscription

Subscribe to predefined market streams like 'nasdaq' or 'iex' for aggregated data.  This feed is only available to users who have completed their user declaration form and have been approved for direct streaming services. For more information, please contact marketdata@financialmodelingprep.com

**Parameters**

| Field | Type | Example |
| --- | --- | --- |
| stream* | string | Exchange:  "nasdaq-basic-w-nls-plus", "iex-tops", "tsx-level-1", "tsxv-level-1", "lse-level-1", "cboe-index-main" \| FMP:  "fmp-crypto-stream", "fmp-index-stream", "fmp-commodity-stream", "fmp-currency-stream", "fmp-us-equities-stream", "fmp-us-otc-stream", "fmp-uk-equities-stream", "fmp-ca-equities-stream" \| Delayed: Add "-delayed" suffix to any stream |

**Example Response**

```json
{
  "symbol": "XKMYA.IS",
  "name": "BIST Kimya Petrol Plastik",
  "price": 13057.45,
  "changesPercentage": 0.35246,
  "change": 45.86,
  "dayLow": 13031.22,
  "dayHigh": 13085.88,
  "yearHigh": 13085.88,
  "yearLow": 13011.59,
  "marketCap": 0,
  "priceAvg50": 13245.1474,
  "priceAvg200": 11936.814,
  "exchange": "INDEX",
  "volume": 0,
  "avgVolume": 0,
  "open": 13051.14,
  "previousClose": 13011.59,
  "eps": null,
  "pe": null,
  "earningsAnnouncement": null,
  "sharesOutstanding": null,
  "timestamp": 1766045220,
  "range": "13011.59 - 13085.88",
  "type": "index",
  "updatedAt": "2025-12-18T08:22:00.504Z"
}
```

---

### Unsubscribe Ticker

Stop receiving updates for a particular ticker.

**Parameters**

| Field | Type | Example |
| --- | --- | --- |
| ticker* | string \| array | "AAPL" or ["AAPL", "MSFT", "^GSPC"] |

---

### Unsubscribe Market Stream

Stop receiving aggregated data from a stream like 'nasdaq' or 'aftermarket'.

**Parameters**

| Field | Type | Example |
| --- | --- | --- |
| stream* | string | Stream identifier to unsubscribe from |

**Example Response**

```json
{
  "event": "unsubscribe",
  "status": 200,
  "message": "Unsubscribed from nasdaq stream."
}
```

---

# Bulk

## Profile

### Company Profile Bulk

The FMP Profile Bulk API allows users to retrieve comprehensive company profile data in bulk. Access essential information, such as company details, stock price, market cap, sector, industry, and more for multiple companies in a single request.

The FMP Profile Bulk API provides detailed profiles of companies across global stock exchanges. This API is ideal for users who need to: Retrieve Comprehensive Data: Access company profiles that include stock prices, market capitalization, industry classification, and more. Bulk Data Requests: Get company details for multiple organizations in one API call, making data collection more efficient. Analyze Company Information: Use this data to gain insights into company operations, leadership, financials, and industry sectors. This API is highly beneficial for financial analysts, data scientists, and anyone needing extensive company profile data for various organizations.

**Endpoint:** `https://financialmodelingprep.com/stable/profile-bulk?part=0`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| part* | string | 0 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "price": 271.36,
    "marketCap": 4009711150080,
    "beta": 1.107,
    "lastDividend": 1.03,
    "range": "169.21-288.62",
    "change": -0.83,
    "changePercentage": -0.30493,
    "volume": 44494594,
    "averageVolume": 48811139,
    "companyName": "Apple Inc.",
    "currency": "USD",
    "cik": "0000320193",
    "isin": "US0378331005",
    "cusip": "037833100",
    "exchangeFullName": "NASDAQ Global Select",
    "exchange": "NASDAQ",
    "industry": "Consumer Electronics",
    "website": "https://www.apple.com",
    "description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide. The company offers iPhone, a line of smartphones; Mac, a line of personal computers; iPad, a line of multi-purpose tablets; and wearables, home, and accessories comprising AirPods, Apple TV, Apple Watch, Beats products, and HomePod. It also provides AppleCare support and cloud services; and operates various platforms, including the App Store that allow customers to discover and download applications and digital content, such as books, music, video, games, and podcasts, as well as advertising services include third-party licensing arrangements and its own advertising platforms. In addition, the company offers various subscription-based services, such as Apple Arcade, a game subscription service; Apple Fitness+, a personalized fitness service; Apple Music, which offers users a curated listening experience with on-demand radio stations; Apple News+, a subscription news and magazine service; Apple TV+, which offers exclusive original content; Apple Card, a co-branded credit card; and Apple Pay, a cashless payment service, as well as licenses its intellectual property. The company serves consumers, and small and mid-sized businesses; and the education, enterprise, and government markets. It distributes third-party applications for its products through the App Store. The company also sells its products through its retail and online stores, and direct sales force; and third-party cellular network carriers, wholesalers, retailers, and resellers. Apple Inc. was founded in 1976 and is headquartered in Cupertino, California.",
    "ceo": "Timothy D. Cook",
    "sector": "Technology",
    "country": "US",
    "fullTimeEmployees": "164000",
    "phone": "(408) 996-1010",
    "address": "One Apple Park Way",
    "city": "Cupertino",
    "state": "CA",
    "zip": "95014",
    "image": "https://images.financialmodelingprep.com/symbol/AAPL.png",
    "ipoDate": "1980-12-12",
    "defaultImage": false,
    "isEtf": false,
    "isActivelyTrading": true,
    "isAdr": false,
    "isFund": false
  }
]
```

---

### Stock Rating Bulk

The FMP Rating Bulk API provides users with comprehensive rating data for multiple stocks in a single request. Retrieve key financial ratings and recommendations such as overall ratings, DCF recommendations, and more for multiple companies at once.

The FMP Rating Bulk API offers detailed rating information for stocks across global exchanges. This API is useful for: Accessing Comprehensive Ratings: Receive ratings based on multiple financial indicators like DCF, ROE, ROA, and PE ratios. Bulk Data Requests: Retrieve rating data for multiple stocks in a single API call, making data retrieval more efficient. Supporting Investment Decisions: Use the rating data to help guide buy, hold, or sell decisions for individual or bulk stocks based on comprehensive financial analysis. This API is valuable for investors, financial analysts, and developers looking to integrate bulk rating data into their platforms or reports.

**Endpoint:** `https://financialmodelingprep.com/stable/rating-bulk`

**Example Response**

```json
[
  {
    "symbol": "000001.SZ",
    "date": "2025-07-09",
    "rating": "B+",
    "discountedCashFlowScore": "5",
    "returnOnEquityScore": "3",
    "returnOnAssetsScore": "2",
    "debtToEquityScore": "1",
    "priceToEarningsScore": "4",
    "priceToBookScore": "4"
  }
]
```

---

### DCF Valuations Bulk

The FMP DCF Bulk API enables users to quickly retrieve discounted cash flow (DCF) valuations for multiple symbols in one request. Access the implied price movement and percentage differences for all listed companies.

The DCF Bulk API offers a convenient way to gather DCF valuations across a wide range of symbols, allowing investors and analysts to: Retrieve DCF Valuations in Bulk: Obtain discounted cash flow valuations for multiple stocks in a single API call, saving time and improving data retrieval efficiency. Analyze Price Movements: Use the DCF percent difference data to evaluate the potential price movement based on the company&rsquo;s valuation. Informed Decision-Making: Leverage bulk DCF data to make strategic investment decisions by comparing DCF values across various companies. This API is ideal for large-scale portfolio managers, financial analysts, and data scientists who need to assess valuations for a large number of companies.

**Endpoint:** `https://financialmodelingprep.com/stable/dcf-bulk`

**Example Response**

```json
[
  {
    "symbol": "000002.SZ",
    "date": "2025-07-09",
    "dcf": "179.6654688379575",
    "Stock Price": "6.54"
  }
]
```

---

### Financial Scores Bulk

The FMP Scores Bulk API allows users to quickly retrieve a wide range of key financial scores and metrics for multiple symbols. These scores provide valuable insights into company performance, financial health, and operational efficiency.

The Scores Bulk API delivers comprehensive financial data, enabling users to analyze the following key metrics: Altman Z-Score: Evaluate a company's likelihood of bankruptcy using this key solvency metric. Piotroski Score: Assess a company's financial strength and performance based on nine criteria. Working Capital &amp; Total Assets: Gain insights into a company&rsquo;s short-term financial health and asset base. Retained Earnings and EBIT: Understand the company's profitability and retained earnings. Market Capitalization &amp; Liabilities: Compare company valuations and debt obligations to gauge financial stability. This API is designed for financial analysts, investors, and institutions who need to evaluate and compare multiple companies at once, making it an efficient solution for bulk financial data retrieval.

**Endpoint:** `https://financialmodelingprep.com/stable/scores-bulk`

**Example Response**

```json
[
  {
    "symbol": "000001.SZ",
    "reportedCurrency": "CNY",
    "altmanZScore": "0.29153682196643543",
    "piotroskiScore": "5",
    "workingCapital": "746131000000",
    "totalAssets": "5777858000000",
    "retainedEarnings": "255621000000",
    "ebit": "32590000000",
    "marketCap": "236751980000",
    "totalLiabilities": "5271746000000",
    "revenue": "167996000000"
  }
]
```

---

### Price Target Summary Bulk

The Price Target Summary Bulk API provides a comprehensive overview of price targets for all listed symbols over multiple timeframes. With this API, users can quickly retrieve price target data, helping investors and analysts compare current prices to projected targets across different periods.

This API enables users to access price targets for all companies, offering insights into: Price Targets Over Timeframes: Retrieve price target data for symbols, including insights for the last month, quarter, year, and all-time periods. Average Price Target: View the average price target set by analysts and market experts for each symbol. Price Target Differences: Analyze the percentage difference between current prices and price targets across various timeframes. Publisher Data: Identify the sources and publishers providing these price targets, offering an understanding of the context and reliability of the data. The Price Target Summary Bulk API is ideal for institutional investors, analysts, and traders seeking a holistic view of stock price forecasts and analyst expectations.

**Endpoint:** `https://financialmodelingprep.com/stable/price-target-summary-bulk`

**Example Response**

```json
[
  {
    "symbol": "A",
    "lastMonthCount": "0",
    "lastMonthAvgPriceTarget": "0",
    "lastQuarterCount": "1",
    "lastQuarterAvgPriceTarget": "116",
    "lastYearCount": "6",
    "lastYearAvgPriceTarget": "142.17",
    "allTimeCount": "18",
    "allTimeAvgPriceTarget": "146.61",
    "publishers": "[\"\"TheFly\""
  }
]
```

---

### ETF Holder Bulk

The ETF Holder Bulk API allows users to quickly retrieve detailed information about the assets and shares held by Exchange-Traded Funds (ETFs). This API provides insights into the weight each asset carries within the ETF, along with key financial information related to these holdings.

The ETF Holder Bulk API enables users to access: Comprehensive Asset Lists: Retrieve a list of all assets held by an ETF, including individual stocks, bonds, and other securities. Share Information: View the number of shares an ETF holds for each asset, providing clarity on the distribution of holdings. Weight Percentage: Analyze the percentage weight of each asset within the ETF, helping investors understand its contribution to the ETF's overall value. Market Value: Get up-to-date market values for each asset held by the ETF, giving a complete picture of the ETF's composition. ISIN and CUSIP Identifiers: Identify assets by their ISIN or CUSIP for more precise tracking and research. The ETF Holder Bulk API is an essential tool for financial analysts, institutional investors, and portfolio managers who need to analyze ETF composition, asset allocation, and potential risks or opportunities.

**Endpoint:** `https://financialmodelingprep.com/stable/etf-holder-bulk?part=1`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| part* | string | 1 |

**Example Response**

```json
[
  {
    "symbol": "EXCH.AS",
    "name": "SAMSUNG ELECTRO MECHANICS LTD",
    "sharesNumber": "15514",
    "asset": "009150.KS",
    "weightPercentage": "0.09611",
    "cusip": "",
    "isin": "KR7009150004",
    "marketValue": "1553142.49",
    "lastUpdated\"": "2024-09-06\""
  }
]
```

---

### Upgrades Downgrades Consensus Bulk

The Upgrades Downgrades Consensus Bulk API provides a comprehensive view of analyst ratings across all symbols. Retrieve bulk data for analyst upgrades, downgrades, and consensus recommendations to gain insights into the market's outlook on individual stocks.

This API allows users to access: Analyst Recommendations: Get detailed ratings such as strong buy, buy, hold, sell, and strong sell for multiple stocks in a single request. Consensus Ratings: View the overall consensus for each stock based on analyst recommendations, helping you assess the general market sentiment. Upgrades and Downgrades Trends: Track recent upgrades or downgrades across different symbols to identify potential investment opportunities or risks. Market Insights: Gain valuable insights into how the market views a stock&rsquo;s future performance, based on expert analysis and recommendations. This API is particularly useful for institutional investors, portfolio managers, and financial analysts who want to monitor stock ratings in bulk, helping them make more informed decisions based on the latest market trends and analyst opinions.

**Endpoint:** `https://financialmodelingprep.com/stable/upgrades-downgrades-consensus-bulk`

**Example Response**

```json
[
  {
    "symbol": "",
    "strongBuy": "0",
    "buy": "1",
    "hold": "1",
    "sell": "0",
    "strongSell": "0",
    "consensus": "Buy"
  }
]
```

---

### Key Metrics TTM Bulk

The Key Metrics TTM Bulk API allows users to retrieve trailing twelve months (TTM) data for all companies available in the database. The API provides critical financial ratios and metrics based on each company’s latest financial report, offering insights into company performance and financial health.

This API gives access to: Market and Enterprise Value Metrics: Get TTM market capitalization, enterprise value, and other valuation multiples such as EV to sales, operating cash flow, and free cash flow. Profitability and Return Ratios: Track key ratios including return on assets (ROA), return on equity (ROE), return on invested capital (ROIC), and more. Operational Efficiency Metrics: Access metrics like the cash conversion cycle, days of payables, receivables, and inventory outstanding, providing insight into a company&rsquo;s operational efficiency. Liquidity and Leverage Ratios: Monitor liquidity with the current ratio and assess financial leverage through net debt to EBITDA and other relevant ratios. Cash Flow and Yield Metrics: Evaluate cash flow-related metrics, such as free cash flow yield, earnings yield, and capex to revenue ratios, helping investors understand how well a company generates and uses cash. This API is especially useful for analysts, portfolio managers, and institutional investors seeking to monitor key financial metrics across a large universe of companies. The API is non-filterable, providing the most recent TTM data based on the latest financial filings.

**Endpoint:** `https://financialmodelingprep.com/stable/key-metrics-ttm-bulk`

**Example Response**

```json
[
  {
    "symbol": "000001.SZ",
    "marketCap": "249171756000",
    "enterpriseValueTTM": "-496959244000",
    "evToSalesTTM": "-2.95816117050406",
    "evToOperatingCashFlowTTM": "-2.9831814247210167",
    "evToFreeCashFlowTTM": "-3.028355803098073",
    "evToEBITDATTM": "-14.656106051669223",
    "netDebtToEBITDATTM": "-22.004571192638906",
    "currentRatioTTM": "0",
    "incomeQualityTTM": "15.217593861331872",
    "grahamNumberTTM": "31.017865999534138",
    "grahamNetNetTTM": "-199.05514330278228",
    "taxBurdenTTM": "0.8225101702576465",
    "interestBurdenTTM": "1.4030970878917606",
    "workingCapitalTTM": "746131000000",
    "investedCapitalTTM": "772543000000",
    "returnOnAssetsTTM": "0.007558510437605078",
    "operatingReturnOnAssetsTTM": "0.013555578495362656",
    "returnOnTangibleAssetsTTM": "0.007576346366296015",
    "returnOnEquityTTM": "0.09082717681735725",
    "returnOnInvestedCapitalTTM": "0.011141314993384131",
    "returnOnCapitalEmployedTTM": "0.013545504233575834",
    "earningsYieldTTM": "0.14960077934639543",
    "freeCashFlowYieldTTM": "0.6585898925077207",
    "capexToOperatingCashFlowTTM": "0.014917130388325619",
    "capexToDepreciationTTM": "1.855862584017924",
    "capexToRevenueTTM": "0.014792018857591847",
    "salesGeneralAndAdministrativeToRevenueTTM": "0.10163337222314817",
    "researchAndDevelopementToRevenueTTM": "0",
    "stockBasedCompensationToRevenueTTM": "0",
    "intangiblesToTotalAssetsTTM": "0.002354159621091415",
    "averageReceivablesTTM": "0",
    "averagePayablesTTM": "0",
    "averageInventoryTTM": "0",
    "daysOfSalesOutstandingTTM": "0",
    "daysOfPayablesOutstandingTTM": "0",
    "daysOfInventoryOutstandingTTM": "0",
    "operatingCycleTTM": "0",
    "cashConversionCycleTTM": "0",
    "freeCashFlowToEquityTTM": "910233000000",
    "freeCashFlowToFirmTTM": "-35237570137.11014",
    "tangibleAssetValueTTM": "492510000000",
    "netCurrentAssetValueTTM": "-4525615000000"
  }
]
```

---

### Ratios TTM Bulk

The Ratios TTM Bulk API offers an efficient way to retrieve trailing twelve months (TTM) financial ratios for stocks. It provides users with detailed insights into a company’s profitability, liquidity, efficiency, leverage, and valuation ratios, all based on the most recent financial report.

With this API, you can access a wide array of financial ratios including: Profitability Ratios: Gross profit margin, operating profit margin, net profit margin, and more, helping investors assess how well a company is generating profit from its operations. Liquidity Ratios: Key liquidity measures such as current ratio, quick ratio, and cash ratio to understand how well a company can meet its short-term liabilities. Efficiency Ratios: Metrics such as receivables turnover, inventory turnover, and asset turnover to evaluate how efficiently a company utilizes its assets. Leverage Ratios: Debt-to-assets, debt-to-equity, and debt-to-capital ratios, which provide insight into a company&rsquo;s capital structure and financial leverage. Valuation Ratios: Ratios such as price-to-earnings (P/E), price-to-book (P/B), and price-to-sales (P/S) to help investors determine whether a stock is overvalued or undervalued. Cash Flow Ratios: Free cash flow yield, operating cash flow coverage, and capital expenditure coverage ratios to assess how well a company manages its cash flow relative to its operations and investments. This API is invaluable for financial analysts, institutional investors, and portfolio managers who need to track and compare TTM ratios across multiple companies for investment decision-making.

**Endpoint:** `https://financialmodelingprep.com/stable/ratios-ttm-bulk`

**Example Response**

```json
[
  {
    "symbol": "000001.SZ",
    "grossProfitMarginTTM": "1.1622776732779352",
    "ebitMarginTTM": "0.22525536322293388",
    "ebitdaMarginTTM": "0.2018381390033096",
    "operatingProfitMarginTTM": "0.4658682349579752",
    "pretaxProfitMarginTTM": "0.3160551441700993",
    "continuousOperationsProfitMarginTTM": "0.25995857044215337",
    "netProfitMarginTTM": "0.25995857044215337",
    "bottomLineProfitMarginTTM": "0.25995857044215337",
    "receivablesTurnoverTTM": "0",
    "payablesTurnoverTTM": "0",
    "inventoryTurnoverTTM": "0",
    "fixedAssetTurnoverTTM": "13.114441842310695",
    "assetTurnoverTTM": "0.029075827062555015",
    "currentRatioTTM": "0",
    "quickRatioTTM": "0",
    "solvencyRatioTTM": "0.008534174446189174",
    "cashRatioTTM": "0",
    "priceToEarningsRatioTTM": "6.68445715569793",
    "priceToEarningsGrowthRatioTTM": "-3.6096068640768793",
    "forwardPriceToEarningsGrowthRatioTTM": "2.4481492401413427",
    "priceToBookRatioTTM": "0.576796465809228",
    "priceToSalesRatioTTM": "1.483200528584014",
    "priceToFreeCashFlowRatioTTM": "1.518395607609901",
    "priceToOperatingCashFlowRatioTTM": "1.7523793147342828",
    "debtToAssetsRatioTTM": "0",
    "debtToEquityRatioTTM": "0",
    "debtToCapitalRatioTTM": "0",
    "longTermDebtToCapitalRatioTTM": "0",
    "financialLeverageRatioTTM": "11.416164801466868",
    "workingCapitalTurnoverRatioTTM": "0.23544250931631752",
    "operatingCashFlowRatioTTM": "0",
    "operatingCashFlowSalesRatioTTM": "0.991612895545132",
    "freeCashFlowOperatingCashFlowRatioTTM": "0.9850828696116743",
    "debtServiceCoverageRatioTTM": "0.24758322210087771",
    "interestCoverageRatioTTM": "0.7914088096104842",
    "shortTermOperatingCashFlowCoverageRatioTTM": "0",
    "operatingCashFlowCoverageRatioTTM": "0",
    "capitalExpenditureCoverageRatioTTM": "67.03702213279678",
    "dividendPaidAndCapexCoverageRatioTTM": "6.192364879934577",
    "dividendPayoutRatioTTM": "0.5590996519509067",
    "dividendYieldTTM": "0.10335",
    "enterpriseValueTTM": "-496959244000",
    "revenuePerShareTTM": "7.389154370023568",
    "netIncomePerShareTTM": "1.9208740068077172",
    "interestDebtPerShareTTM": "4.349676503966586",
    "cashPerShareTTM": "32.81790720767194",
    "bookValuePerShareTTM": "22.260885357516656",
    "tangibleBookValuePerShareTTM": "21.662613507347245",
    "shareholdersEquityPerShareTTM": "22.260885357516656",
    "operatingCashFlowPerShareTTM": "7.327180760489036",
    "capexPerShareTTM": "0.10930051078304583",
    "freeCashFlowPerShareTTM": "7.21788024970599",
    "netIncomePerEBTTTM": "0.8225101702576465",
    "ebtPerEbitTTM": "0.6784217520188082",
    "priceToFairValueTTM": "0.576796465809228",
    "debtToMarketCapTTM": "0",
    "effectiveTaxRateTTM": "0.17748982974235347",
    "enterpriseValueMultipleTTM": "-14.656106051669223",
    "dividendPerShareTTM": "1.327"
  }
]
```

---

### Stock Peers Bulk

The Stock Peers Bulk API allows you to quickly retrieve a comprehensive list of peer companies for all stocks in the database. By accessing this data, you can easily compare a stock’s performance with its closest competitors or similar companies within the same industry or sector.

This API is designed to help investors, analysts, and portfolio managers: Identify Competitors: Get a list of peer companies that operate in the same industry or offer similar products/services. Benchmark Performance: Compare a company's financial performance and stock metrics against its peers to gauge relative strength or weaknesses. Strategic Analysis: Use peer data to conduct industry-level analyses, helping to uncover trends or opportunities within a sector. Investment Decisions: Evaluate whether a company stands out or lags behind its competitors in terms of key metrics such as revenue growth, profitability, or stock price performance. This bulk data API simplifies the process of finding peer companies for multiple stocks in one query, making it a valuable tool for deeper market analysis.

**Endpoint:** `https://financialmodelingprep.com/stable/peers-bulk`

**Example Response**

```json
[
  {
    "symbol": "000001.SZ",
    "peers": "600036.SS"
  }
]
```

---

### Earnings Surprises Bulk

The Earnings Surprises Bulk API allows users to retrieve bulk data on annual earnings surprises, enabling quick analysis of which companies have beaten, missed, or met their earnings estimates. This API provides actual versus estimated earnings per share (EPS) for multiple companies at once, offering valuable insights for investors and analysts.

The Earnings Surprises Bulk API is an essential tool for those who want to: Identify Performance Trends: Track whether companies consistently beat or miss earnings estimates. Investment Opportunities: Spot potential investment opportunities in companies that are exceeding earnings expectations or facing downward trends due to missed estimates. Analyze Market Sentiment: Gauge investor confidence by analyzing how a company's earnings performance compares to market expectations. Strategic Forecasting: Use historical data to enhance financial forecasting models or make data-driven investment decisions. With this bulk API, you can easily retrieve earnings surprises data for multiple companies, simplifying the process of spotting trends across different industries or sectors.

**Endpoint:** `https://financialmodelingprep.com/stable/earnings-surprises-bulk?year=2026`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| year* | string | 2026 |

**Example Response**

```json
[
  {
    "symbol": "AMKYF",
    "date": "2025-07-09",
    "epsActual": "0.3631",
    "epsEstimated": "0.3615",
    "lastUpdated": "2025-07-09"
  }
]
```

---

## Financials

### Income Statement Bulk

The Bulk Income Statement API allows users to retrieve detailed income statement data in bulk. This API is designed for large-scale data analysis, providing comprehensive insights into a company's financial performance, including revenue, gross profit, expenses, and net income.

The Bulk Income Statement API is ideal for users who need to: Analyze Financial Performance: Access large datasets for deep financial analysis, including multiple income statements from various companies. Track Revenue and Profit Trends: Quickly retrieve data on revenue, gross profit, operating income, and net income to assess a company's profitability over time. Evaluate Expenses: Review operating expenses, cost of revenue, and selling, general, and administrative expenses (SG&amp;A) to identify where a company allocates its spending. Conduct Bulk Research: Ideal for financial analysts, investors, and researchers who need to process income statements across multiple companies for detailed industry or sector comparison. This API delivers financial data in a standardized format, making it easy to conduct large-scale financial analysis.

**Endpoint:** `https://financialmodelingprep.com/stable/income-statement-bulk?year=2026&period=Q1`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| year* | string | 2026 |
| period* | string | Q1,Q2,Q3,Q4,FY |

**Example Response**

```json
[
  {
    "date": "2025-03-31",
    "symbol": "000001.SZ",
    "reportedCurrency": "CNY",
    "cik": "0000000000",
    "filingDate": "2025-03-31",
    "acceptedDate": "2025-03-31 00:00:00",
    "fiscalYear": "2025",
    "period": "Q1",
    "revenue": "33644000000",
    "costOfRevenue": "0",
    "grossProfit": "33644000000",
    "researchAndDevelopmentExpenses": "0",
    "generalAndAdministrativeExpenses": "9055000000",
    "sellingAndMarketingExpenses": "0",
    "sellingGeneralAndAdministrativeExpenses": "9055000000",
    "otherExpenses": "314000000",
    "operatingExpenses": "9369000000",
    "costAndExpenses": "9369000000",
    "netInterestIncome": "22788000000",
    "interestIncome": "44938000000",
    "interestExpense": "22150000000",
    "depreciationAndAmortization": "0",
    "ebitda": "16802000000",
    "ebit": "0",
    "nonOperatingIncomeExcludingInterest": "24275000000",
    "operatingIncome": "24275000000",
    "totalOtherIncomeExpensesNet": "-7392000000",
    "incomeBeforeTax": "16883000000",
    "incomeTaxExpense": "2787000000",
    "netIncomeFromContinuingOperations": "14096000000",
    "netIncomeFromDiscontinuedOperations": "0",
    "otherAdjustmentsToNetIncome": "0",
    "netIncome": "14096000000",
    "netIncomeDeductions": "0",
    "bottomLineNetIncome": "14096000000",
    "eps": "0.62",
    "epsDiluted": "0.62",
    "weightedAverageShsOut": "22735483871",
    "weightedAverageShsOutDil": "22735483871"
  }
]
```

---

### Income Statement Growth Bulk

The Bulk Income Statement Growth API provides access to growth data for income statements across multiple companies. Track and analyze growth trends over time for key financial metrics such as revenue, net income, and operating income, enabling a better understanding of corporate performance trends.

This API is ideal for users who want to: Track Financial Growth: Understand how a company&rsquo;s income statement figures, like revenue and net income, are growing over time. Analyze Trends: Gain insights into long-term trends in income statement growth, including expenses, EBITDA, and earnings per share (EPS). Evaluate Performance: Measure a company&rsquo;s growth rate across multiple financial metrics to evaluate its financial health and performance over time. Bulk Data Retrieval: Quickly retrieve growth data for income statements across a large number of companies for comparative analysis or trend forecasting.

**Endpoint:** `https://financialmodelingprep.com/stable/income-statement-growth-bulk?year=2026&period=Q1`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| year* | string | 2026 |
| period* | string | Q1,Q2,Q3,Q4,FY |

**Example Response**

```json
[
  {
    "symbol": "000001.SZ",
    "date": "2025-03-31",
    "fiscalYear": "2025",
    "period": "Q1",
    "reportedCurrency": "CNY",
    "growthRevenue": "-0.04159070191431176",
    "growthCostOfRevenue": "0",
    "growthGrossProfit": "-0.04159070191431176",
    "growthGrossProfitRatio": "0",
    "growthResearchAndDevelopmentExpenses": "0",
    "growthGeneralAndAdministrativeExpenses": "1.7466809598416757",
    "growthSellingAndMarketingExpenses": "0",
    "growthOtherExpenses": "-0.9860376183912135",
    "growthOperatingExpenses": "-0.095830920671685",
    "growthCostAndExpenses": "-0.095830920671685",
    "growthInterestIncome": "-0.003105727849505302",
    "growthInterestExpense": "-0.08421879522057303",
    "growthDepreciationAndAmortization": "0",
    "growthEBITDA": "0",
    "growthOperatingIncome": "-0.018874787810201278",
    "growthIncomeBeforeTax": "1.4139262224764084",
    "growthIncomeTaxExpense": "0.2582392776523702",
    "growthNetIncome": "1.9495710399665203",
    "growthEPS": "1.6956521739130435",
    "growthEPSDiluted": "1.6956521739130435",
    "growthWeightedAverageShsOut": "0.09825852256371011",
    "growthWeightedAverageShsOutDil": "0.09825852256371011",
    "growthEBIT": "1",
    "growthNonOperatingIncomeExcludingInterest": "-0.5659209985158163",
    "growthNetInterestIncome": "0.09080465272126753",
    "growthTotalOtherIncomeExpensesNet": "0.5835023664638269",
    "growthNetIncomeFromContinuingOperations": "1.9495710399665203",
    "growthOtherAdjustmentsToNetIncome": "0",
    "growthNetIncomeDeductions": "0"
  }
]
```

---

### Balance Sheet Statement Bulk

The Bulk Balance Sheet Statement API provides comprehensive access to balance sheet data across multiple companies. It enables users to analyze financial positions by retrieving key figures such as total assets, liabilities, and equity. Ideal for comparing the financial health and stability of different companies on a large scale.

This API is a powerful tool for: Financial Analysis: Retrieve balance sheet data to evaluate assets, liabilities, and equity, and assess the financial health of multiple companies. Bulk Data Retrieval: Get detailed financial positions for a wide range of companies in a single request, allowing for comparative analysis and portfolio evaluation. Corporate Health Assessment: Analyze metrics such as total debt, cash and cash equivalents, net receivables, and shareholder equity to determine the strength of a company&rsquo;s balance sheet. Historical Tracking: Use balance sheet data to track a company&rsquo;s financial position over time, identifying trends and changes in its financial standing.

**Endpoint:** `https://financialmodelingprep.com/stable/balance-sheet-statement-bulk?year=2026&period=Q1`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| year* | string | 2026 |
| period* | string | Q1,Q2,Q3,Q4,FY |

**Example Response**

```json
[
  {
    "date": "2025-03-31",
    "symbol": "MTLRP.ME",
    "reportedCurrency": "RUB",
    "cik": "0000000000",
    "filingDate": "2025-05-31",
    "acceptedDate": "2025-03-31 07:00:00",
    "fiscalYear": "2025",
    "period": "Q1",
    "cashAndCashEquivalents": "1985000",
    "shortTermInvestments": "0",
    "cashAndShortTermInvestments": "1985000",
    "netReceivables": "9666577000",
    "accountsReceivables": "9666577000",
    "otherReceivables": "0",
    "inventory": "4520000",
    "prepaids": "0",
    "otherCurrentAssets": "27293000",
    "totalCurrentAssets": "9700830000",
    "propertyPlantEquipmentNet": "194000",
    "goodwill": "0",
    "intangibleAssets": "5665000",
    "goodwillAndIntangibleAssets": "5665000",
    "longTermInvestments": "237373355000",
    "taxAssets": "791813000",
    "otherNonCurrentAssets": "0",
    "totalNonCurrentAssets": "238171027000",
    "otherAssets": "0",
    "totalAssets": "247871857000",
    "totalPayables": "3861497000",
    "accountPayables": "3861497000",
    "otherPayables": "0",
    "accruedExpenses": "0",
    "shortTermDebt": "4842848000",
    "capitalLeaseObligationsCurrent": "0",
    "taxPayables": "2484576000",
    "deferredRevenue": "0",
    "otherCurrentLiabilities": "146647000",
    "totalCurrentLiabilities": "8851455000",
    "longTermDebt": "178923999000",
    "capitalLeaseObligationsNonCurrent": "0",
    "deferredRevenueNonCurrent": "0",
    "deferredTaxLiabilitiesNonCurrent": "737391000",
    "otherNonCurrentLiabilities": "52574304000",
    "totalNonCurrentLiabilities": "232235780000",
    "otherLiabilities": "0",
    "capitalLeaseObligations": "0",
    "totalLiabilities": "244087635000",
    "treasuryStock": "0",
    "preferredStock": "0",
    "commonStock": "5550277000",
    "retainedEarnings": "-5066509000",
    "additionalPaidInCapital": "6023340000",
    "accumulatedOtherComprehensiveIncomeLoss": "0",
    "otherTotalStockholdersEquity": "0",
    "totalStockholdersEquity": "6784622000",
    "totalEquity": "6784622000",
    "minorityInterest": "0",
    "totalLiabilitiesAndTotalEquity": "247871857000",
    "totalInvestments": "237373355000",
    "totalDebt": "183766847000",
    "netDebt": "183764862000"
  }
]
```

---

### Balance Sheet Statement Growth Bulk

The Balance Sheet Growth Bulk API allows users to retrieve growth data across multiple companies’ balance sheets, enabling detailed analysis of how financial positions have changed over time.

This API is designed for: Trend Analysis: Track the growth or decline of financial metrics such as cash and short-term investments, receivables, total liabilities, and equity. Comparative Insights: Analyze changes in financial positions across multiple companies over different periods to spot trends, risks, and opportunities. Long-Term Financial Health Assessment: Assess how a company&rsquo;s balance sheet has evolved, providing deeper insights into its long-term financial stability. This API is essential for tracking the development of assets, liabilities, and equity, providing insights into a company&rsquo;s financial trajectory.

**Endpoint:** `https://financialmodelingprep.com/stable/balance-sheet-statement-growth-bulk?year=2026&period=Q1`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| year* | string | 2026 |
| period* | string | Q1,Q2,Q3,Q4,FY |

**Example Response**

```json
[
  {
    "symbol": "000001.SZ",
    "date": "2025-03-31",
    "fiscalYear": "2025",
    "period": "Q1",
    "reportedCurrency": "CNY",
    "growthCashAndCashEquivalents": "0.09574482145872953",
    "growthShortTermInvestments": "0",
    "growthCashAndShortTermInvestments": "0.09574482145872953",
    "growthNetReceivables": "0",
    "growthInventory": "0",
    "growthOtherCurrentAssets": "0",
    "growthTotalCurrentAssets": "0.09574482145872953",
    "growthPropertyPlantEquipmentNet": "-0.06373337231398918",
    "growthGoodwill": "0",
    "growthIntangibleAssets": "-0.03270278935556268",
    "growthGoodwillAndIntangibleAssets": "-0.01477618426770969",
    "growthLongTermInvestments": "-0.0774117797082201",
    "growthTaxAssets": "0",
    "growthOtherNonCurrentAssets": "0.07678934705504345",
    "growthTotalNonCurrentAssets": "-0.01112505367669385",
    "growthOtherAssets": "0.001488576544346165",
    "growthTotalAssets": "0.001488576544346165",
    "growthAccountPayables": "0",
    "growthShortTermDebt": "0",
    "growthTaxPayables": "-0.0279424216765453",
    "growthDeferredRevenue": "0",
    "growthOtherCurrentLiabilities": "0.12022416350749959",
    "growthTotalCurrentLiabilities": "0",
    "growthLongTermDebt": "0",
    "growthDeferredRevenueNonCurrent": "0",
    "growthDeferredTaxLiabilitiesNonCurrent": "0",
    "growthOtherNonCurrentLiabilities": "0",
    "growthTotalNonCurrentLiabilities": "0",
    "growthOtherLiabilities": "-0.0005084911577141635",
    "growthTotalLiabilities": "-0.0005084911577141635",
    "growthPreferredStock": "0",
    "growthCommonStock": "0",
    "growthRetainedEarnings": "0.049325752755485314",
    "growthAccumulatedOtherComprehensiveIncomeLoss": "0",
    "growthOthertotalStockholdersEquity": "-0.0035208940994345805",
    "growthTotalStockholdersEquity": "0.022774946346510602",
    "growthMinorityInterest": "0",
    "growthTotalEquity": "0.022774946346510602",
    "growthTotalLiabilitiesAndStockholdersEquity": "0.001488576544346165",
    "growthTotalInvestments": "-0.0774117797082201",
    "growthTotalDebt": "0",
    "growthNetDebt": "-0.09574482145872953",
    "growthAccountsReceivables": "0",
    "growthOtherReceivables": "0",
    "growthPrepaids": "0",
    "growthTotalPayables": "-0.12022416350749959",
    "growthOtherPayables": "-0.12022416350749959",
    "growthAccruedExpenses": "0",
    "growthCapitalLeaseObligationsCurrent": "0",
    "growthAdditionalPaidInCapital": "0",
    "growthTreasuryStock": "0"
  }
]
```

---

### Cash Flow Statement Bulk

The Cash Flow Statement Bulk API provides access to detailed cash flow reports for a wide range of companies. This API enables users to retrieve bulk cash flow statement data, helping to analyze companies’ operating, investing, and financing activities over time.

This API is essential for: Tracking Cash Movements: Understand how a company generates and uses cash in its operations, investments, and financing activities. Free Cash Flow Analysis: Analyze free cash flow to assess a company's ability to generate cash after accounting for capital expenditures. Comparative Analysis: Access data for multiple companies at once to compare their cash flow trends, helping to identify companies with strong or weak cash flow management.

**Endpoint:** `https://financialmodelingprep.com/stable/cash-flow-statement-bulk?year=2026&period=Q1`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| year* | string | 2026 |
| period* | string | Q1,Q2,Q3,Q4,FY |

**Example Response**

```json
[
  {
    "date": "2025-03-31",
    "symbol": "000001.SZ",
    "reportedCurrency": "CNY",
    "cik": "0000000000",
    "filingDate": "2025-03-31",
    "acceptedDate": "2025-03-31 00:00:00",
    "fiscalYear": "2025",
    "period": "Q1",
    "netIncome": "0",
    "depreciationAndAmortization": "0",
    "deferredIncomeTax": "0",
    "stockBasedCompensation": "0",
    "changeInWorkingCapital": "0",
    "accountsReceivables": "0",
    "inventory": "0",
    "accountsPayables": "0",
    "otherWorkingCapital": "0",
    "otherNonCashItems": "162946000000",
    "netCashProvidedByOperatingActivities": "162946000000",
    "investmentsInPropertyPlantAndEquipment": "-338000000",
    "acquisitionsNet": "0",
    "purchasesOfInvestments": "-227916000000",
    "salesMaturitiesOfInvestments": "253172000000",
    "otherInvestingActivities": "25000000",
    "netCashProvidedByInvestingActivities": "24943000000",
    "netDebtIssuance": "0",
    "longTermNetDebtIssuance": "0",
    "shortTermNetDebtIssuance": "0",
    "netStockIssuance": "0",
    "netCommonStockIssuance": "0",
    "commonStockIssuance": "0",
    "commonStockRepurchased": "0",
    "netPreferredStockIssuance": "0",
    "netDividendsPaid": "-2538000000",
    "commonDividendsPaid": "-2538000000",
    "preferredDividendsPaid": "0",
    "otherFinancingActivities": "-155860000000",
    "netCashProvidedByFinancingActivities": "-158398000000",
    "effectOfForexChangesOnCash": "-130000000",
    "netChangeInCash": "29361000000",
    "cashAtEndOfPeriod": "286307000000",
    "cashAtBeginningOfPeriod": "256946000000",
    "operatingCashFlow": "162946000000",
    "capitalExpenditure": "-338000000",
    "freeCashFlow": "162608000000",
    "incomeTaxesPaid": "0",
    "interestPaid": "0"
  }
]
```

---

### Cash Flow Statement Growth Bulk

The Cash Flow Statement Growth Bulk API allows you to retrieve bulk growth data for cash flow statements, enabling you to track changes in cash flows over time. This API is ideal for analyzing the cash flow growth trends of multiple companies simultaneously.

This API helps you: Track Growth Trends: Monitor changes in key cash flow metrics such as operating cash flow, capital expenditures, and free cash flow over time. Compare Company Performance: Quickly analyze the growth in cash flow activities for several companies, making it easier to identify high-growth firms or companies with declining cash flow. Understand Financial Health: Evaluate how companies are managing their cash flow, whether it&rsquo;s through improved operations or changes in investment and financing activities.

**Endpoint:** `https://financialmodelingprep.com/stable/cash-flow-statement-growth-bulk?year=2026&period=Q1`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| year* | string | 2026 |
| period* | string | Q1,Q2,Q3,Q4,FY |

**Example Response**

```json
[
  {
    "symbol": "000001.SZ",
    "date": "2025-03-31",
    "fiscalYear": "2025",
    "period": "Q1",
    "reportedCurrency": "CNY",
    "growthNetIncome": "0",
    "growthDepreciationAndAmortization": "0",
    "growthDeferredIncomeTax": "0",
    "growthStockBasedCompensation": "0",
    "growthChangeInWorkingCapital": "0",
    "growthAccountsReceivables": "0",
    "growthInventory": "0",
    "growthAccountsPayables": "0",
    "growthOtherWorkingCapital": "0",
    "growthOtherNonCashItems": "3.2072823819457614",
    "growthNetCashProvidedByOperatingActivites": "3.2072823819457614",
    "growthInvestmentsInPropertyPlantAndEquipment": "0.7332280978689818",
    "growthAcquisitionsNet": "0",
    "growthPurchasesOfInvestments": "-0.12254537395030414",
    "growthSalesMaturitiesOfInvestments": "0.3847853673478318",
    "growthOtherInvestingActivites": "-0.8417721518987342",
    "growthNetCashUsedForInvestingActivites": "2.1699343339587243",
    "growthDebtRepayment": "1",
    "growthCommonStockIssued": "0",
    "growthCommonStockRepurchased": "0",
    "growthDividendsPaid": "0.6798284344644885",
    "growthOtherFinancingActivites": "-1.7077146619443309",
    "growthNetCashUsedProvidedByFinancingActivities": "-3.2122934677858628",
    "growthEffectOfForexChangesOnCash": "-1.0731570061902083",
    "growthNetChangeInCash": "2.348938711752274",
    "growthCashAtEndOfPeriod": "0.11426914604625096",
    "growthCashAtBeginningOfPeriod": "-0.07809495106059301",
    "growthOperatingCashFlow": "3.2072823819457614",
    "growthCapitalExpenditure": "0.7332280978689818",
    "growthFreeCashFlow": "3.16553689621649",
    "growthNetDebtIssuance": "1",
    "growthLongTermNetDebtIssuance": "1",
    "growthShortTermNetDebtIssuance": "0",
    "growthNetStockIssuance": "0",
    "growthPreferredDividendsPaid": "0.6798284344644885",
    "growthIncomeTaxesPaid": "0",
    "growthInterestPaid": "0"
  }
]
```

---

## Chart

### Eod Bulk

The EOD Bulk API allows users to retrieve end-of-day stock price data for multiple symbols in bulk. This API is ideal for financial analysts, traders, and investors who need to assess valuations for a large number of companies.

The EOD Bulk API provides: Historical Stock Prices: Access end-of-day stock prices for multiple symbols on a specific date. Open, High, Low, Close Prices: Retrieve detailed price data, including opening, high, low, and closing prices for each symbol. Volume and Adjusted Close: Get trading volume and adjusted closing prices to analyze stock performance and trading activity. Historical Data Analysis: Use historical stock prices to conduct technical analysis, backtesting, and trend forecasting. This API is designed for users who need to analyze stock prices across a wide range of companies, making it an efficient solution for bulk data retrieval.

**Endpoint:** `https://financialmodelingprep.com/stable/eod-bulk?date=2024-10-22`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| date* | string | 2024-10-22 |

**Example Response**

```json
[
  {
    "symbol": "EGS745W1C011.CA",
    "date": "2024-10-22",
    "open": "2.67",
    "low": "2.7",
    "high": "2.9",
    "close": "2.93",
    "adjClose": "2.93",
    "volume": "920904"
  }
]
```

---

# Partners

## TipRanks Search

### Analyst Ratings Search

Full TipRanks analyst ratings search. Returns each individual analyst rating sourced from TipRanks, including the specific recommendation and price target from a given analyst, the action taken, the originating article/source, the price target currency (converted by default, native when nonadjusted=true), and the analyst's identity (name, firm, expertUID). Filterable by symbol, expertUID and recommendation date range, ordered newest first.

The TipRanks Analyst Ratings Search API provides a chronological feed of every analyst recommendation sourced from TipRanks, making it the primary search interface across the full ratings history. This endpoint offers: Analyst Identity: Each result names the analyst, their firm and a stable expertUID you can pass to the point-in-time endpoints. Recommendation & Action: The rating itself (Buy / Hold / Sell) alongside the action taken — for example an initiation, upgrade, downgrade or maintained call. Price Targets: Converted into a common currency by default, or returned in their native currency when nonadjusted=true is supplied. Article Attribution: A headline, source site and link back to the originating article so each call can be traced to its publication. Flexible Filters: Narrow by symbol, focus on a single analyst with expertUID, or bound a window with from and to; pagination is controlled via limit (max 5000) and page. Results are ordered newest first, so the endpoint is well suited to powering activity feeds, analyst-driven research dashboards and historical backfills for a watchlist.

> **Note:** Ratings history only goes back 3 years. For analyst ratings older than 3 years, contact support — historical backfill requires an Enterprise plan.

**Endpoint:** `https://financialmodelingprep.com/stable/tipranks-search`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| expertUID | string |  |
| symbol | string | AAPL |
| from | date | 2025-06-10 |
| to | date | 2026-06-10 |
| limit | number | 100 |
| page | number | 0 |
| nonadjusted | boolean | false |

**Example Response**

```json
[
  {
    "symbol": "GB:0J3K",
    "date": "2026-05-21T17:40:11.370Z",
    "recommendationDate": "2026-05-21",
    "expertUID": "3c6eb8cf1347a4e5757e628fccb684a93abee587",
    "analystName": "Keegan Cox",
    "firmName": "D.A. Davidson",
    "recommendation": "Hold",
    "analystAction": "maintained",
    "articleTitle": "Analysts Offer Insights on Consumer Cyclical Companies: Hasbro (NASDAQ: HAS) and Burlington Stores (NYSE: BURL)",
    "articleSite": "TipRanks Contributor",
    "priceTarget": null,
    "priceTargetCurrency": null,
    "priceTargetCurrencyCode": null,
    "url": "https://www.tipranks.com/news/blurbs/analysts-offer-insights-on-consumer-cyclical-companies-hasbro-has-and-burlington-stores-burl-blurbs-news"
  }
]
```

---

## TipRanks PIT Latest

### Point in time Ratings by Symbol

Point-in-time summary of a symbol's analyst ratings as of a chosen date. Queries all ratings on the ticker from that date and prior, collapsing the history to each analyst's latest active call (one row per expertUID) and surfacing per-analyst statistics — analystRank, stockSuccessRate and stockAvgReturn — alongside the price target. Price targets are FX-converted by default (nonadjusted=true for native currency).

The TipRanks Point in time Ratings by Symbol API answers a focused question: as of a given date, what did every analyst covering this ticker have on the books? Instead of streaming every historical rating, it collapses the history so each analyst appears once with their most recent active call. This endpoint offers: Coverage Panel: One row per analyst with the latest recommendation, the price target attached to that call, and the article that triggered it. Analyst Quality: Each row includes the analyst's overall analystRank, historical stockSuccessRate and stockAvgReturn for the ticker, so consumers can weight credibility inline. Historical Snapshots: An optional date parameter rolls the snapshot backwards, letting you reconstruct what the consensus looked like at any prior point in time. Currency Control: Price targets are FX-converted by default; pass nonadjusted=true to receive native-currency values. Pagination: Standard limit (default 100, max 5000) and page parameters for large coverage universes. The compact, one-row-per-analyst shape makes this endpoint a natural fit for stock-page coverage panels and current-consensus widgets.

> **Note:** Ratings history only goes back 3 years. For historical analyst ratings beyond that window, contact support — it requires an Enterprise plan.

**Endpoint:** `https://financialmodelingprep.com/stable/tipranks-pit-symbol?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| date | string | 2026-06-10 |
| limit | number | 100 |
| page | number | 0 |
| nonadjusted | boolean | false |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "date": "2026-04-25T12:22:04.000Z",
    "expertUID": "5d31ea120f0c9a13ca43b3b56771f5114138c8c2",
    "analystName": "Jim Kelleher",
    "stockSuccessRate": 0.92,
    "firmName": "Argus Research",
    "lastRecommendation": "buy",
    "lastRecommendationDate": "2026-04-21",
    "articleTitle": "Apple (AAPL) Receives a Rating Update from a Top Analyst",
    "articleSite": "TipRanks Contributor",
    "priceTarget": 325,
    "priceTargetCurrency": "USD",
    "url": "https://www.tipranks.com/news/blurbs/apple-aapl-receives-a-rating-update-from-a-top-analyst-blurbs-news-3",
    "lastAnalystAction": "reiterated",
    "stockReturn": -0.0329,
    "beatTarget": false
  }
]
```

---

### Point in time Ratings by Analyst

Point-in-time summary of a single analyst's ratings as of a chosen date. Queries all of the analyst's ratings from that date and prior, returning one row per symbol they cover with their latest active call, the attached price target, and per-row statistics (analystRank, stockSuccessRate, stockAvgReturn). Targets are FX-converted by default (nonadjusted=true for native currency).

The TipRanks Point In Time Ratings by Analyst API inverts the symbol-centric view: instead of asking who covers a stock, it asks what a single analyst's active book looks like. Supply an expertUID and the response returns one entry per ticker the analyst covers, each carrying their most recent recommendation as of the chosen date. This endpoint offers: Analyst Book: A portfolio-style view of every name the analyst currently covers, with their last call collapsed to a single row per symbol. Price Targets & Articles: The latest published target on each ticker along with the article and source site that triggered the rating. Performance Context: analystRank, stockSuccessRate and stockAvgReturn travel with every row, ready to render alongside the call. Historical Reconstructions: A date parameter rewinds the snapshot, so you can see what an analyst's book looked like at any past point. Currency & Pagination: nonadjusted=true returns native-currency targets, while limit (max 5000) and page handle large coverage lists. The endpoint is purpose-built for analyst profile pages and any view that needs to surface an analyst's open positions at a glance.

> **Note:** Ratings history only goes back 3 years. For historical analyst ratings beyond that window, contact support — it requires an Enterprise plan.

**Endpoint:** `https://financialmodelingprep.com/stable/tipranks-pit-analyst`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| expertUID | string |  |
| analystName | string | Analyst Name |
| date | string | 2026-06-10 |
| limit | number | 100 |
| page | number | 0 |
| nonadjusted | boolean | false |

**Example Response**

```json
[
  {
    "symbol": "0J3K.L",
    "date": "2026-05-21T13:40:11.370Z",
    "expertUID": "3c6eb8cf1347a4e5757e628fccb684a93abee587",
    "analystName": "Keegan Cox",
    "stockSuccessRate": 0,
    "firmName": "D.A. Davidson",
    "lastRecommendation": "Hold",
    "lastRecommendationDate": "2026-05-21",
    "articleTitle": "Analysts Offer Insights on Consumer Cyclical Companies: Hasbro (NASDAQ: HAS) and Burlington Stores (NYSE: BURL)",
    "articleSite": "TipRanks Contributor",
    "priceTarget": null,
    "priceTargetCurrency": null,
    "url": "https://www.tipranks.com/news/blurbs/analysts-offer-insights-on-consumer-cyclical-companies-hasbro-has-and-burlington-stores-burl-blurbs-news",
    "lastAnalystAction": "maintained",
    "stockReturn": null,
    "beatTarget": null
  }
]
```

---

## TipRanks Summary

### Ratings Summary by Symbol

Aggregated rollup of all TipRanks ratings on a single ticker over a date window. Returns one row with totalRecommendations plus distinctAnalysts covering the name, a recommendation breakdown (buy/hold/sell) and analyst-action breakdown (initiated/maintained/upgraded/downgraded/reiterated/resumed). Also includes price-target accuracy stats: validPriceTargets and comparedPriceTargets counts, beats vs misses, and return metrics (averageReturn, topReturn, worstReturn). Window defaults to the trailing twelve months.

The TipRanks Ratings Summary by Symbol API rolls up every Tipranks rating on a single ticker into a single summary record over the chosen window. Rather than returning each rating individually, it tallies how the Street has been positioning on the name. This endpoint offers: Consensus Breakdown: Counts of each distinct recommendation (Buy, Hold, Sell) issued on the ticker during the window. Action Mix: Counts of each kind of analyst action — for example initiations, upgrades, downgrades and reiterations — so volume and tone can be inspected together. Total Activity: A totalRecommendations counter that summarises how much research the ticker attracted in the period. Configurable Window: from and to bound the recommendation date range; the default window is the trailing twelve months. The endpoint returns a single compact row, which makes it ideal for consensus chips, headline widgets and screener-scale fan-outs across a watchlist.

**Endpoint:** `https://financialmodelingprep.com/stable/tipranks-symbol-summary?symbol=AAPL`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| symbol* | string | AAPL |
| from | date | 2025-06-10 |
| to | date | 2026-06-10 |

**Example Response**

```json
[
  {
    "symbol": "AAPL",
    "from": "2025-07-08",
    "to": "2026-07-08",
    "totalRecommendations": 420,
    "distinctSymbols": 1,
    "distinctAnalysts": 45,
    "validPriceTargets": 372,
    "recommendations": {
      "buy": 272,
      "hold": 126,
      "sell": 22
    },
    "analystAction": {
      "initiated": 3,
      "maintained": 310,
      "upgraded": 14,
      "downgraded": 4,
      "reiterated": 89,
      "resumed": 0
    },
    "comparedPriceTargets": 372,
    "beats": 246,
    "misses": 126,
    "averageReturn": 0.1108,
    "topReturn": 0.7852,
    "worstReturn": -0.2279
  }
]
```

---

### Ratings Summary by Analyst

Aggregated rollup of every recommendation a single analyst (expertUID) has issued over a date window. Returns one row with totalRecommendations plus distinctSymbols covered, a recommendation breakdown (buy/hold/sell) and analyst-action breakdown (initiated/maintained/upgraded/downgraded/reiterated/resumed). Also includes the analyst's price-target track record: validPriceTargets and comparedPriceTargets counts, beats vs misses, and return metrics (averageReturn, topReturn, worstReturn). Window defaults to the trailing twelve months.

The TipRanks Ratings Summary by Analyst API characterises a single analyst's posture over a chosen window by tallying every recommendation they have issued. This endpoint offers: Recommendation Mix: A count of each distinct rating (Buy, Hold, Sell) the analyst has published in the window, exposing how bullish or bearish their book has been. Action Profile: A breakdown of analyst actions — initiations, maintenances, upgrades, downgrades and so on — capturing how often the analyst is changing their view. Activity Volume: A totalRecommendations counter that quantifies coverage activity over the window. Configurable Window: expertUID selects the analyst, while optional from and to parameters bound the date range (defaulting to the trailing twelve months). The compact, single-row response is well suited to analyst profile metrics, side-by-side comparison tables and research-quality scoring.

**Endpoint:** `https://financialmodelingprep.com/stable/tipranks-analyst-summary?expertUID=3c6eb8cf1347a4e5757e628fccb684a93abee587`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| expertUID* | string | 3c6eb8cf1347a4e5757e628fccb684a93abee587 |
| from | date | 2025-06-10 |
| to | date | 2026-06-10 |

**Example Response**

```json
[
  {
    "expertUID": "3c6eb8cf1347a4e5757e628fccb684a93abee587",
    "from": "2025-07-08",
    "to": "2026-07-08",
    "totalRecommendations": 24,
    "distinctSymbols": 8,
    "distinctAnalysts": 1,
    "validPriceTargets": 15,
    "recommendations": {
      "buy": 19,
      "hold": 5,
      "sell": 0
    },
    "analystAction": {
      "initiated": 0,
      "maintained": 22,
      "upgraded": 0,
      "downgraded": 0,
      "reiterated": 2,
      "resumed": 0
    },
    "comparedPriceTargets": 15,
    "beats": 2,
    "misses": 13,
    "averageReturn": -0.2439,
    "topReturn": 0.3284,
    "worstReturn": -0.6505
  }
]
```

---

### Ratings Summary by Firm

Aggregated rollup of all ratings issued by analysts at a given firm over a date window. Pools the whole desk into one row with totalRecommendations plus distinctAnalysts and distinctSymbols, a recommendation breakdown (buy/hold/sell) and analyst-action breakdown (initiated/maintained/upgraded/downgraded/reiterated/resumed). Also includes desk-wide price-target accuracy: validPriceTargets and comparedPriceTargets counts, beats vs misses, and return metrics (averageReturn, topReturn, worstReturn). firmName must match the data exactly (e.g. 'Morgan Stanley'). Window defaults to the trailing twelve months.

The TipRanks Ratings Summary by Firm API aggregates TipRanks activity at the firm level, pooling every analyst at a given firm into a single summary of what the desk has been publishing. This endpoint offers: Desk-Wide Consensus: A count of each distinct recommendation (Buy, Hold, Sell) issued by the firm's analysts in the window. Action Footprint: A breakdown of the kinds of actions the desk has taken — initiations, upgrades, downgrades, reiterations and the rest. Coverage Volume: A totalRecommendations counter that captures how active the firm has been over the period. Configurable Window: firmName selects the firm (matched exactly as it appears in the data, e.g. Morgan Stanley); from and to bound the window (defaulting to the trailing twelve months). The single-row response is purpose-built for firm-comparison views and for surfacing a sell-side desk's footprint on a research page without enumerating every individual report.

**Endpoint:** `https://financialmodelingprep.com/stable/tipranks-firm-summary?firmName=Morgan Stanley`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| firmName* | string | Morgan Stanley |
| from | date | 2025-06-10 |
| to | date | 2026-06-10 |

**Example Response**

```json
[
  {
    "firmName": "Morgan Stanley",
    "from": "2025-07-08",
    "to": "2026-07-08",
    "totalRecommendations": 13848,
    "distinctSymbols": 4176,
    "distinctAnalysts": 261,
    "validPriceTargets": 13698,
    "recommendations": {
      "buy": 6029,
      "hold": 6153,
      "sell": 1666
    },
    "analystAction": {
      "initiated": 281,
      "maintained": 11429,
      "upgraded": 358,
      "downgraded": 430,
      "reiterated": 1346,
      "resumed": 4
    },
    "comparedPriceTargets": 13520,
    "beats": 4990,
    "misses": 8530,
    "averageReturn": -0.015,
    "topReturn": 23.7828,
    "worstReturn": -1
  }
]
```

---

## Tipranks Analysts

### Analyst Directory Lookup

Analyst directory lookup by name. Resolves a TipRanks analyst profile, returning the stable expertUID used by the other TipRanks endpoints, the analyst's firm and profile image, star rating (numOfStars), and aggregate performance metrics (successRate, excessReturn, totalRecommendations, goodRecommendations). No fuzzy matching — analystName must be passed exactly as published.

The TipRanks Analyst Directory Lookup API is the canonical resolver for Tipranks analyst profiles. Given an analyst's name it returns the full profile record needed to render an analyst page or to bridge into the rating and summary endpoints. This endpoint offers: Stable Identifier: The expertUID that other Tipranks endpoints expect as input. Biographical Block: The analyst's firm and profile picture URL, ready to power a profile header. Star Rating: The numOfStars rating Tipranks assigns based on track record. Performance Metrics: Aggregate quality statistics including overall successRate, average excessReturn, plus totalRecommendations and goodRecommendations counters. Provide the analyst's name in analystName exactly as it is published (for example Andrew Marok); the endpoint does not perform fuzzy matching, so callers should reuse names as returned by the search or point-in-time endpoints.

**Endpoint:** `https://financialmodelingprep.com/stable/tipranks-analysts`

**Parameters**

| Query Parameter | Type | Example |
| --- | --- | --- |
| page | number | 0 |
| limit | number | 1000 |
| firmName | string | Morgan Stanley |

**Example Response**

```json
[
  {
    "expertUID": "00201afb944bc31fe5fdf769a76490d5f41ca8a4",
    "analystName": "Liam Robertson",
    "firmName": "Jarden",
    "successRate": 0.545,
    "excessReturn": 0.11,
    "totalRecommendations": 44,
    "goodRecommendations": 24,
    "analystRank": 3168,
    "numOfStars": 3.7
  },
  {
    "expertUID": "0026d747820947da6a9b62a45ea2962d96936bd0",
    "analystName": "Rishabh Gupta",
    "firmName": "J.P. Morgan",
    "successRate": 0.571,
    "excessReturn": 0.002,
    "totalRecommendations": 7,
    "goodRecommendations": 4,
    "analystRank": 8252,
    "numOfStars": 1.6
  }
]
```

---
