//+------------------------------------------------------------------+
//| IW_Export.mq4 — Investor Watch v1.09 (MT4 Strategy Scan)          |
//| GitHub Actions Windows par MT4 start hote hi ye SCRIPT chalta hai: |
//| investor login ka account info, poori order history, open trades, |
//| pending orders, symbol info aur candles -> MQL4\Files\IW_export.json|
//| Kabhi trade NAHI karta (read-only).                               |
//+------------------------------------------------------------------+
#property strict

//@@DLL_START
#import "user32.dll"
int GetAncestor(int hwnd, int flags);
int PostMessageW(int hwnd, int msg, int wparam, int lparam);
#import
//@@DLL_END

int    fh = INVALID_HANDLE;
string syms[];

void W(string s) { FileWriteString(fh, s); }

string Esc(string s)
{
   string o = "";
   int n = StringLen(s);
   for(int i = 0; i < n; i++)
   {
      ushort c = StringGetCharacter(s, i);
      if(c == '"' || c == '\\') o += "\\" + ShortToString(c);
      else if(c < 32) o += " ";
      else o += ShortToString(c);
   }
   return o;
}

string D(double v, int dg = 5) { return DoubleToString(v, dg); }

void Done(string msg)
{
   int h = FileOpen("IW_done.txt", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h != INVALID_HANDLE) { FileWriteString(h, msg); FileClose(h); }
   Print("IW_Export: ", msg);
}

void AddSym(string s)
{
   if(s == "") return;
   for(int i = 0; i < ArraySize(syms); i++) if(syms[i] == s) return;
   int n = ArraySize(syms);
   ArrayResize(syms, n + 1);
   syms[n] = s;
}

void LoadAllHistory()
{
//@@DLL_START
   if(!IsDllsAllowed()) { Print("IW_Export: DLL off — terminal ki default history hi milegi"); return; }
   int main = GetAncestor(WindowHandle(Symbol(), Period()), 2);   // GA_ROOT
   if(main != 0) PostMessageW(main, 0x0111, 33058, 0);             // WM_COMMAND, "All History"
//@@DLL_END
}

void OrderRow(bool first)
{
   if(!first) W(",");
   W("{\"t\":" + IntegerToString(OrderTicket()) + ",\"ty\":" + IntegerToString(OrderType()) +
     ",\"s\":\"" + Esc(OrderSymbol()) + "\",\"v\":" + D(OrderLots(), 2) +
     ",\"ot\":" + IntegerToString((long)OrderOpenTime()) + ",\"op\":" + D(OrderOpenPrice(), 6) +
     ",\"ct\":" + IntegerToString((long)OrderCloseTime()) + ",\"cp\":" + D(OrderClosePrice(), 6) +
     ",\"sl\":" + D(OrderStopLoss(), 6) + ",\"tp\":" + D(OrderTakeProfit(), 6) +
     ",\"pr\":" + D(OrderProfit(), 2) + ",\"cm\":" + D(OrderCommission(), 2) + ",\"sw\":" + D(OrderSwap(), 2) +
     ",\"mg\":" + IntegerToString(OrderMagicNumber()) + ",\"ex\":" + IntegerToString((long)OrderExpiration()) +
     ",\"c\":\"" + Esc(OrderComment()) + "\"}");
}

void Candles(string s, int tf, string name, datetime from, datetime to)
{
   MqlRates r[];
   int n = -1;
   for(int k = 0; k < 25 && !IsStopped(); k++)
   {
      ResetLastError();
      n = CopyRates(s, tf, from, to, r);
      if(n > 0) break;
      Sleep(1500);
   }
   W("\"" + name + "\":[");
   for(int i = 0; i < n; i++)
   {
      if(i) W(",");
      W("[" + IntegerToString((long)r[i].time) + "," + D(r[i].open, 6) + "," + D(r[i].high, 6) + "," + D(r[i].low, 6) + "," + D(r[i].close, 6) + "]");
   }
   W("]");
   Print("IW_Export: candles ", s, " ", name, " = ", n);
}

void OnStart()
{
   FileDelete("IW_done.txt");
   // 1) login / connection ka intezaar
   int w = 0;
   while(!IsStopped() && (!IsConnected() || AccountNumber() == 0) && w < 150) { Sleep(1000); w++; }
   if(!IsConnected() || AccountNumber() == 0) { Done("error: login nahi hua — password / server galat?"); return; }
   Sleep(3000);

   // 2) "All History" + history sync hone ka intezaar
   LoadAllHistory();
   int last = -1, same = 0;
   for(int k = 0; k < 45 && same < 4 && !IsStopped(); k++)
   {
      int n = OrdersHistoryTotal();
      if(n == last) same++; else { same = 0; last = n; }
      Sleep(2000);
   }

   fh = FileOpen("IW_export.json", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(fh == INVALID_HANDLE) { Done("error: file nahi bani " + IntegerToString(GetLastError())); return; }

   bool trade_ok = (AccountInfoInteger(ACCOUNT_TRADE_ALLOWED) != 0);
   W("{\"acct\":{\"login\":" + IntegerToString(AccountNumber()) + ",\"server\":\"" + Esc(AccountServer()) +
     "\",\"company\":\"" + Esc(AccountCompany()) + "\",\"currency\":\"" + Esc(AccountCurrency()) +
     "\",\"balance\":" + D(AccountBalance(), 2) + ",\"equity\":" + D(AccountEquity(), 2) +
     ",\"margin\":" + D(AccountMargin(), 2) + ",\"profit\":" + D(AccountProfit(), 2) +
     ",\"leverage\":" + IntegerToString(AccountLeverage()) + ",\"demo\":" + (IsDemo() ? "true" : "false") +
     ",\"trade_allowed\":" + (trade_ok ? "true" : "false") + "}");
   W(",\"now_server\":" + IntegerToString((long)TimeCurrent()) + ",\"now_gmt\":" + IntegerToString((long)TimeGMT()));

   // 3) history (band trades + cancel/expire pending + balance)
   datetime first = TimeCurrent();
   W(",\"history\":[");
   int hn = OrdersHistoryTotal();
   bool f1 = true;
   for(int i = 0; i < hn; i++)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_HISTORY)) continue;
      OrderRow(f1); f1 = false;
      if(OrderType() <= 5) { AddSym(OrderSymbol()); if(OrderOpenTime() < first) first = OrderOpenTime(); }
   }
   W("]");

   // 4) abhi khule trades + pending
   W(",\"trades\":[");
   f1 = true;
   for(int i = 0; i < OrdersTotal(); i++)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      OrderRow(f1); f1 = false;
      AddSym(OrderSymbol());
      if(OrderOpenTime() < first) first = OrderOpenTime();
   }
   W("]");

   // 5) symbol info
   W(",\"symbols\":{");
   int ns = ArraySize(syms);
   if(ns > 12) ns = 12;
   for(int i = 0; i < ns; i++)
   {
      string s = syms[i];
      SymbolSelect(s, true);
      if(i) W(",");
      W("\"" + Esc(s) + "\":{\"point\":" + D(MarketInfo(s, MODE_POINT), 8) + ",\"digits\":" + IntegerToString((int)MarketInfo(s, MODE_DIGITS)) +
        ",\"contract\":" + D(MarketInfo(s, MODE_LOTSIZE), 2) + ",\"tick_value\":" + D(MarketInfo(s, MODE_TICKVALUE), 6) +
        ",\"tick_size\":" + D(MarketInfo(s, MODE_TICKSIZE), 8) + ",\"vol_min\":" + D(MarketInfo(s, MODE_MINLOT), 2) +
        ",\"vol_step\":" + D(MarketInfo(s, MODE_LOTSTEP), 2) + ",\"spread\":" + IntegerToString((int)MarketInfo(s, MODE_SPREAD)) + "}");
   }
   W("}");

   // 6) candles (M1 = 60 din, baaki pehle trade se 5 din pehle tak)
   W(",\"candles\":{");
   datetime to = TimeCurrent() + 86400;
   datetime from = first - 5 * 86400;
   datetime m1from = from;
   if(TimeCurrent() - 60 * 86400 > from) m1from = TimeCurrent() - 60 * 86400;
   for(int i = 0; i < ns && !IsStopped(); i++)
   {
      string s = syms[i];
      if(i) W(",");
      W("\"" + Esc(s) + "\":{");
      Candles(s, PERIOD_M1, "M1", m1from, to);  W(",");
      Candles(s, PERIOD_M5, "M5", from, to);    W(",");
      Candles(s, PERIOD_M15, "M15", from, to);  W(",");
      Candles(s, PERIOD_H1, "H1", from, to);
      W("}");
   }
   W("}}");
   FileClose(fh);
   Done("ok " + IntegerToString(hn) + " history, " + IntegerToString(OrdersTotal()) + " open");
}
