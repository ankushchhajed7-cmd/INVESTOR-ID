//+------------------------------------------------------------------+
//| IW_Recorder.mq4 — Investor Watch v1.11.2 (Live Record, MT4)       |
//| SCRIPT (EA nahi — EA runner par init nahi hota tha).               |
//| Investor login ke saath har 200 ms: symbol ka bid/ask (badle to)   |
//| + sab open orders ka snapshot (lot/open/SL/TP badle to)            |
//| -> MQL4\Files\IW_rec.csv.  Kabhi trade NAHI karta.                 |
//| Config: MQL4\Files\IW_rec_cfg.txt = "minute,SYMBOL"                |
//+------------------------------------------------------------------+
#property strict

int fh = INVALID_HANDLE;

void Done(string msg)
{
   int h = FileOpen("IW_rec_done.txt", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h != INVALID_HANDLE) { FileWriteString(h, msg); FileClose(h); }
   Print("IW_Recorder: ", msg);
}

string Snap()
{
   string s = "";
   for(int i = 0; i < OrdersTotal(); i++)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      s += IntegerToString(OrderTicket()) + ":" + IntegerToString(OrderType()) + ":" + OrderSymbol() + ":" +
           DoubleToString(OrderLots(), 2) + ":" + DoubleToString(OrderOpenPrice(), 5) + ":" +
           DoubleToString(OrderStopLoss(), 5) + ":" + DoubleToString(OrderTakeProfit(), 5) + ":" +
           IntegerToString(OrderMagicNumber()) + ":" + IntegerToString((long)OrderOpenTime()) + ";";
   }
   return s;
}

void OnStart()
{
   FileDelete("IW_rec_done.txt");
   int minutes = 180;
   string sym = "GOLD";
   int h = FileOpen("IW_rec_cfg.txt", FILE_READ | FILE_TXT | FILE_ANSI);
   if(h != INVALID_HANDLE)
   {
      string c = FileReadString(h); FileClose(h);
      string p[];
      int n = StringSplit(c, ',', p);
      if(n >= 1) minutes = (int)StringToInteger(p[0]);
      if(n >= 2 && StringLen(p[1]) > 0) sym = p[1];
   }
   if(minutes <= 0) minutes = 180;

   int w = 0;
   while(!IsStopped() && (!IsConnected() || AccountNumber() == 0) && w < 150) { Sleep(1000); w++; }
   if(!IsConnected() || AccountNumber() == 0) { Done("error: login nahi hua"); return; }
   SymbolSelect(sym, true);
   Sleep(2000);
   int dg = (int)MarketInfo(sym, MODE_DIGITS);

   fh = FileOpen("IW_rec.csv", FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(fh == INVALID_HANDLE) { Done("error: file " + IntegerToString(GetLastError())); return; }
   FileWriteString(fh, "I," + IntegerToString((long)TimeCurrent()) + "," + IntegerToString((long)TimeGMT()) + "," + sym + "," +
                   IntegerToString(AccountNumber()) + "," + IntegerToString(minutes) + "\n");
   FileFlush(fh);
   Print("IW_Recorder: start ", minutes, " min, symbol ", sym);

   datetime t_end = TimeLocal() + minutes * 60;
   double lb = 0, la = 0;
   string last = "";
   long nt = 0;
   uint lastflush = GetTickCount();
   while(!IsStopped() && TimeLocal() < t_end)
   {
      RefreshRates();
      double b = MarketInfo(sym, MODE_BID), a = MarketInfo(sym, MODE_ASK);
      if(b != lb || a != la)
      {
         FileWriteString(fh, "T," + IntegerToString(GetTickCount()) + "," + IntegerToString((long)TimeCurrent()) + "," +
                         DoubleToString(b, dg) + "," + DoubleToString(a, dg) + "\n");
         lb = b; la = a; nt++;
      }
      string s = Snap();
      if(s != last)
      {
         FileWriteString(fh, "S," + IntegerToString(GetTickCount()) + "," + IntegerToString((long)TimeCurrent()) + "," +
                         DoubleToString(b, dg) + "," + DoubleToString(a, dg) + "," + s + "\n");
         last = s;
         FileFlush(fh);
      }
      if(GetTickCount() - lastflush > 10000) { FileFlush(fh); lastflush = GetTickCount(); }
      Sleep(200);
   }
   FileClose(fh);
   Done("ok " + IntegerToString((int)nt) + " ticks");
}
