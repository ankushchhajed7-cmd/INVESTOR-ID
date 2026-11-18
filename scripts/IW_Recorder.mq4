//+------------------------------------------------------------------+
//| IW_Recorder.mq4 — Investor Watch v1.11 (Live Record, MT4)         |
//| GitHub Actions par investor login ke saath chart par chalta hai.  |
//| Har tick (bid/ask) + har second sab orders ka snapshot (SL/TP/lot |
//| badle to) MQL4\Files\IW_rec.csv me likhta hai. Kabhi trade NAHI.  |
//| Minutes: MQL4\Files\IW_rec_cfg.txt se (default 180).              |
//+------------------------------------------------------------------+
#property strict

int    fh = INVALID_HANDLE;
int    minutes = 180;
datetime t_end = 0;
string last_snap = "";
long   n_ticks = 0;

void Done(string msg)
{
   int h = FileOpen("IW_rec_done.txt", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h != INVALID_HANDLE) { FileWriteString(h, msg); FileClose(h); }
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

int OnInit()
{
   FileDelete("IW_rec_done.txt");
   int h = FileOpen("IW_rec_cfg.txt", FILE_READ | FILE_TXT | FILE_ANSI);
   if(h != INVALID_HANDLE) { minutes = (int)StringToInteger(FileReadString(h)); FileClose(h); }
   if(minutes <= 0) minutes = 180;
   fh = FileOpen("IW_rec.csv", FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(fh == INVALID_HANDLE) { Done("error: file"); return INIT_FAILED; }
   t_end = TimeLocal() + minutes * 60;
   FileWriteString(fh, "I," + IntegerToString((long)TimeCurrent()) + "," + IntegerToString((long)TimeGMT()) + "," + Symbol() + "," +
                   IntegerToString(AccountNumber()) + "," + IntegerToString(minutes) + "\n");
   EventSetTimer(1);
   Print("IW_Recorder: start ", minutes, " min on ", Symbol());
   return INIT_SUCCEEDED;
}

void OnTick()
{
   if(fh == INVALID_HANDLE) return;
   n_ticks++;
   FileWriteString(fh, "T," + IntegerToString(GetTickCount()) + "," + IntegerToString((long)TimeCurrent()) + "," +
                   DoubleToString(Bid, Digits) + "," + DoubleToString(Ask, Digits) + "\n");
   Check();
}

void OnTimer()
{
   Check();
   if(TimeLocal() >= t_end)
   {
      FileFlush(fh);
      FileClose(fh); fh = INVALID_HANDLE;
      Done("ok " + IntegerToString((int)n_ticks) + " ticks");
      EventKillTimer();
   }
}

void Check()
{
   if(fh == INVALID_HANDLE) return;
   if(!IsConnected()) return;
   string s = Snap();
   if(s != last_snap)
   {
      FileWriteString(fh, "S," + IntegerToString(GetTickCount()) + "," + IntegerToString((long)TimeCurrent()) + "," +
                      DoubleToString(MarketInfo(Symbol(), MODE_BID), Digits) + "," + DoubleToString(MarketInfo(Symbol(), MODE_ASK), Digits) + "," + s + "\n");
      last_snap = s;
      FileFlush(fh);
   }
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(fh != INVALID_HANDLE) { FileClose(fh); Done("stopped " + IntegerToString(reason)); }
}
