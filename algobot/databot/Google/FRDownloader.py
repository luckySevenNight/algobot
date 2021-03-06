"""
algobot::databot::Google
================================================

API to download data from Google finance:

http://www.google.com/finance

Author: Yue Zhao (yzhao0527'at'gmail'dot'com)
Last Modified: 2014-11-15
"""
from urllib import request
from bs4 import BeautifulSoup
import itertools, time
import numpy as np
import pandas as pd

from ..stock_downloader import StockDownloader
from ..batch_downloader import BatchDownloader
from . import fr_codes


class FRDownloader(StockDownloader):
    """
    Financial Report Data Dowload
    """

    URL = r'https://www.google.com/finance?q={}&fstype=ii'
    Exchanges = set(['NYSE', 'NASDAQ'])
    
    formIds     = ['inc{}div', 'bal{}div', 'cas{}div']
    frequencies = ['interim', 'annual']

    
    def __init__(self, ticker=None, exchange=None):
        StockDownloader.__init__(self, ticker, exchange)

    
    def download(self):
        """
        download the entire HTML file from Google finance

        Return
        ------
        
        """
        assert isinstance(self.ticker, str)
        assert len(self.ticker) > 0
        if self.exchange is None:
            url = self.URL.format(self.ticker)
        else:
            assert self.exchange in self.Exchanges
            url = self.URL.format(r"{}:{}".format(self.exchange,
                                                  self.ticker))

        # load data from web
        try:
            response = request.urlopen(url)
            html = response.read()
        except:
            print("Warning: download failed for {}".format(self.ticker))
        else:
            self.done = True
            self.__parseResult(html)
            

    def __parseResult(self, html):
        """
        """
        soup = BeautifulSoup(html)

        data = {}
        for fid, freq in itertools.product(self.formIds, self.frequencies):
            # Iterate throught 3 forms and 2 frequencies
            formId  = fid.format(freq)
            frame   = soup.find(id=formId)
            fsTable = frame.find(id="fs-table")
            rows    = fsTable.findAll("tr")
    
            header  = [x.text.strip() for x in rows[0].findAll("th")][1:]
            index   = []
            content = []
            for rr in rows[1:]:
                cols  = rr.findAll("td")
                index.append(cols[0].text.strip())
                items = [x.text.strip().replace(",","") for x in cols[1:]]
                content.append(items)
            
            # convert rowname to code
            z = [fr_codes.name_dict[inx] 
            if inx in fr_codes.name_dict 
            else np.NaN for inx in index]
            codes = [b for a, b in z]
            
            m = np.array(content)
            m[m == '-'] = "NaN"
            m.astype(np.float64)
            data[formId] = pd.DataFrame(m, columns=header, index=codes, dtype=np.float64)

        self.data = data
        self.done = True



class FRBatchDownloader(BatchDownloader):


    def __init__(self, tickers=[]):
        print("@TODO: rewrite this part, add exchange data")
        self.downloaders = {}
        for t in tickers:
            self.addTicker(t)
    

    def addTicker(self, ticker, exchange=None):
        self.downloaders[ticker] = FRDownloader(ticker, exchange)
    
        
    def download(self, blink=1, interval=30, n_iter=10):
        n_iter = max(1, n_iter)
        for loop in range(n_iter):
            allDone = True
            for k, v in self.downloaders.items():
                print("process {}".format(k))
                try:
                    v.download()
                except:
                    pass
                else:
                    if not v.done: allDone = False
                time.sleep(blink)
            if allDone: break
            time.sleep(interval)
    
    
    def makeTable(self):
        """
        Make the FR Table
        -----------------
        N-by-M

        N: number of stocks
        M: number of fields
        """
        allData = []
        tickers = []
        for ticker, v in self.downloaders.items():
            formIds     = FRDownloader.formIds
            frequencies = FRDownloader.frequencies

            dta = []
            for fid, freq in itertools.product(formIds, frequencies):
                formId = fid.format(freq)
                for i in range(v.data[formId].shape[1]):
                    z = v.data[formId].iloc[:,i]
                    if freq == 'annual':                        
                        inx = z.index.map(lambda n : "IA{}_{}".format(i, n))
                    else:
                        inx = z.index.map(lambda n : "IQ{}_{}".format(i, n))
                    dta.append(pd.Series(np.array(z), index=inx))

            allData.append(pd.concat(dta))
            tickers.append(ticker)
                        
        tbl = pd.concat(allData, axis=1).T
        tbl.index = tickers
        return tbl
