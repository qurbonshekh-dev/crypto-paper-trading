var COINS = [
  ['Bitcoin','BTC'],
  ['Ethereum','ETH'],
  ['Tether','USDT'],
  ['BNB','BNB'],
  ['XRP','XRP'],
  ['USDC','USDC'],
  ['Solana','SOL'],
  ['TRON','TRX'],
  ['Figure Heloc','FIGR_HELOC'],
  ['Hyperliquid','HYPE'],
  ['Zcash','ZEC'],
  ['Dogecoin','DOGE'],
  ['Rain','RAIN'],
  ['USDS','USDS'],
  ['Chainlink','LINK'],
  ['Monero','XMR'],
  ['WhiteBIT Coin','WBT'],
  ['LEO Token','LEO'],
  ['Cardano','ADA'],
  ['Stellar','XLM'],
  ['Bitcoin Cash','BCH'],
  ['Dai','DAI'],
  ['Canton','CC'],
  ['USD1','USD1'],
  ['Ethena USDe','USDE'],
  ['Gram (prev. Toncoin)','GRAM'],
  ['Litecoin','LTC'],
  ['Hedera','HBAR'],
  ['Global Dollar','USDG'],
  ['Avalanche','AVAX'],
  ['Shiba Inu','SHIB'],
  ['Sui','SUI'],
  ['Cronos','CRO'],
  ['Uniswap','UNI'],
  ['Circle USYC','USYC'],
  ['Tether Gold','XAUT'],
  ['BlackRock USD Institutional Digital Liquidity Fund','BUIDL'],
  ['PayPal USD','PYUSD'],
  ['MemeCore','M'],
  ['NEAR Protocol','NEAR'],
  ['Bittensor','TAO'],
  ['OKB','OKB'],
  ['Ondo US Dollar Yield','USDY'],
  ['Ripple USD','RLUSD'],
  ['Aave','AAVE'],
  ['PAX Gold','PAXG'],
  ['Pump.fun','PUMP'],
  ['Aster','ASTER'],
  ['World Liberty Financial','WLFI'],
  ['Ondo','ONDO'],
  ['Morpho','MORPHO'],
  ['Mantle','MNT'],
  ['Ethena','ENA'],
  ['Pepe','PEPE'],
  ['Sky','SKY'],
  ['HTX DAO','HTX'],
  ['Worldcoin','WLD'],
  ['Polkadot','DOT'],
  ['USDD','USDD'],
  ['Bitget Token','BGB'],
  ['Internet Computer','ICP'],
  ['Falcon USD','USDF'],
  ['BFUSD','BFUSD'],
  ['United Stables','U'],
  ['USDGO','USDGO'],
  ['Ethereum Classic','ETC'],
  ['Spiko Amundi Overnight Swap Fund (EUR)','EURSAFO'],
  ['POL (ex-MATIC)','POL'],
  ['Bitway','BTW'],
  ['Pi Network','PI'],
  ['KuCoin','KCS'],
  ['Blockchain Capital','BCAP'],
  ['Quant','QNT'],
  ['Lighter','LIT'],
  ['Spiko EU T-Bills Money Market Fund','EUTBL'],
  ['Venice Token','VVV'],
  ['Janus Henderson Anemoy Treasury Fund','JTRSY'],
  ['Gate','GT'],
  ['NEXO','NEXO'],
  ['Algorand','ALGO'],
  ['Invesco Short Duration US Government Securities Fund','USTB'],
  ['Cosmos Hub','ATOM'],
  ['Render','RENDER'],
  ['JUST','JST'],
  ['Kaspa','KAS'],
  ['Jupiter','JUP'],
  ['​​Stable','STABLE'],
  ['Janus Henderson Anemoy AAA CLO Fund','JAAA'],
  ['GHO','GHO'],
  ['YLDS','YLDS']
];

// дата покупки, монета, цена покупки, сумма, дата продажи, цена продажи, комментарий
var TRADES = [
  ['2025-11-07','ETH',3308,50,'2025-11-09',3531,''],
  ['2025-11-07','BNB',947,55,'','',''],
  ['2025-11-12','SOL',154.88,53,'','',''],
  ['2025-11-14','SOL',143.76,11,'','',''],
  ['2025-12-02','BNB',830.29,60,'',895,'дата продажи не была записана'],
  ['2025-12-02','SOL',127,30,'',140,'дата продажи не была записана'],
  ['2025-12-02','ETH',2802,40,'',3194,'дата продажи не была записана'],
  ['2025-12-02','DOGE',0.13576,30,'',0.15,'дата продажи не была записана'],
  ['2026-01-08','XRP',2.162,46,'','',''],
  ['2026-01-10','ZEC',381,50,'',409,'дата продажи не была записана'],
  ['2026-01-16','ZEC',416,40,'','',''],
  ['2026-01-16','DOGE',0.14072,40,'','',''],
  ['2026-01-19','ZEC',365,52,'','',''],
  ['2026-01-19','ZEC',303,105,'','','']
];

// ═══════════════════════════════════════════════════════════════
//  ТРЕКЕР КРИПТОСДЕЛОК — строит таблицу целиком, прямо здесь.
//
//  Установка:
//    1. Создай пустую Google Таблицу
//    2. Расширения → Apps Script
//    3. Удали всё, вставь этот файл целиком, сохрани (Ctrl+S)
//    4. Вверху выбери функцию "setup" и нажми «Выполнить»
//    5. Разреши доступ (предупреждение о непроверенном приложении — нормально,
//       разработчик здесь ты сам)
//
//  Всё остальное скрипт сделает сам: три листа, оформление, формулы,
//  выпадающий список монет, перенос сделок и первая загрузка цен.
// ═══════════════════════════════════════════════════════════════

var SH_TRADES = 'Сделки', SH_PRICES = 'Цены', SH_TOTAL = 'Итоги';

/**
 * Разделитель аргументов в формулах: в русской (и почти любой европейской)
 * локали это ';', в английской ','. Определяем опытом, а не догадкой:
 * пишем =SUM(1,1) и смотрим, получилось 2 или нет.
 */
var SEP = ',';
function detectSep_(ss) {
  var sh = ss.getSheets()[0];
  var probe = sh.getRange(sh.getMaxRows(), sh.getMaxColumns());
  try {
    probe.setFormula('=SUM(1,1)');
    SpreadsheetApp.flush();
    SEP = (probe.getValue() === 2) ? ',' : ';';
  } catch (e) {
    SEP = ';';
  }
  probe.clear();
  return SEP;
}
/** Переводит формулу из «запятой» в разделитель этой таблицы. */
function f_(s) { return SEP === ',' ? s : s.split(',').join(';'); }
var ROWS = 100;                       // строк под сделки

var INK='#16202B', SLATE='#1F2933', BRONZE='#A9762B', CREAM='#FFF8E7',
    WHITE='#FFFFFF', LINE='#E1E7EC', MUTED='#6B7A88',
    UP='#0F7B4F', DOWN='#B03A2E', WARN='#9A6B15', ALARM='#FDE2DE', HERO='#FBFAF6';
var TXT='Roboto', NUM='Roboto Mono';

function onOpen() {
  SpreadsheetApp.getUi().createMenu('Трекер')
    .addItem('Обновить цены', 'updatePrices')
    .addSeparator()
    .addItem('Включить автообновление (раз в час)', 'installTrigger')
    .addItem('Выключить автообновление', 'removeTriggers')
    .addSeparator()
    .addItem('Починить формулы (#ERROR!)', 'repairFormulas')
    .addSeparator()
    .addItem('Пересобрать таблицу заново — СТИРАЕТ сделки', 'setup')
    .addToUi();
}

/** Главная: строит всё с нуля. */
function setup() {
  var ss = SpreadsheetApp.getActive();
  detectSep_(ss);
  buildPrices_(ss);
  buildTrades_(ss);
  buildTotals_(ss);
  updatePrices();
  setupDropdown_(ss);

  // убрать посторонние листы (например «Лист1», созданный по умолчанию)
  var keep = [SH_TRADES, SH_PRICES, SH_TOTAL];
  ss.getSheets().slice().forEach(function (s) {
    if (keep.indexOf(s.getName()) === -1) {
      try { ss.deleteSheet(s); } catch (e) {}
    }
  });
  ss.setActiveSheet(ss.getSheetByName(SH_TRADES));
  ss.toast('Таблица собрана. Заполняй кремовые столбцы.', 'Готово', 8);
}

/** Дата из строки YYYY-MM-DD в местной полуночи — без сдвига на день. */
function d_(str) {
  var p = String(str).split('-');
  return new Date(+p[0], +p[1] - 1, +p[2]);
}

function sheet_(ss, name) {
  var sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);
  var f = sh.getFilter();
  if (f) f.remove();                                   // иначе createFilter() упадёт
  sh.clear();
  sh.clearConditionalFormatRules();
  var all = sh.getRange(1, 1, sh.getMaxRows(), sh.getMaxColumns());
  all.breakApart();                                    // иначе merge() упадёт
  try { all.setDataValidation(null); } catch (e) {}
  sh.setHiddenGridlines(true);
  return sh;
}

function titleBar_(sh, cols, text, sub) {
  sh.getRange(1, 1, 1, cols).merge()
    .setValue('  ' + text).setBackground(SLATE).setFontColor(WHITE)
    .setFontFamily(TXT).setFontSize(15).setFontWeight('bold')
    .setVerticalAlignment('middle');
  sh.setRowHeight(1, 34);
  if (sub) {
    sh.getRange(2, 1, 1, cols).merge().setValue('   ' + sub)
      .setFontFamily(TXT).setFontSize(9).setFontColor(MUTED).setFontStyle('italic');
    sh.setRowHeight(2, 20);
  }
}

// ─────────────────── ЛИСТ «СДЕЛКИ» ───────────────────
function buildTrades_(ss) {
  var sh = sheet_(ss, SH_TRADES);
  titleBar_(sh, 14, 'ЖУРНАЛ СДЕЛОК',
    'Кремовые столбцы заполняешь ты. Белые считаются сами. ' +
    '«Цена расчёта»: пока сделка открыта — текущая цена с листа «Цены», ' +
    'после ввода цены продажи — она же, чтобы результат закрытой сделки больше не менялся.');

  var hdr = ['Дата\nпокупки','Монета','Цена\nпокупки','Сумма\nпокупки','Дата\nпродажи',
             'Цена\nпродажи','Кол-во\nмонет','Статус','Цена\nрасчёта','Стоимость\nсейчас',
             'Разница $','Разница %','Дней','Комментарий'];
  sh.getRange(4, 1, 1, 14).setValues([hdr])
    .setBackground(SLATE).setFontColor(WHITE).setFontFamily(TXT)
    .setFontSize(9).setFontWeight('bold')
    .setHorizontalAlignment('center').setVerticalAlignment('middle')
    .setWrap(true).setBorder(true, true, true, true, true, true, LINE, null);
  sh.setRowHeight(4, 40);
  sh.setFrozenRows(4);

  var first = 5, last = 4 + ROWS;

  writeTradeFormulas_(sh);

  // перенос сделок

  var vals = [];
  for (var i = 0; i < TRADES.length; i++) {
    var t = TRADES[i];
    vals.push([t[0] ? d_(t[0]) : '', t[1], t[2], t[3],
               t[4] ? d_(t[4]) : '', t[5] === '' ? '' : t[5]]);
  }
  if (vals.length) sh.getRange(first, 1, vals.length, 6).setValues(vals);
  var notes = TRADES.map(function (t) { return [t[6]]; });
  if (notes.length) sh.getRange(first, 14, notes.length, 1).setValues(notes);

  // оформление
  var body = sh.getRange(first, 1, ROWS, 14);
  body.setBorder(true, true, true, true, true, true, LINE, null)
      .setFontFamily(TXT).setFontSize(10).setFontColor(INK).setVerticalAlignment('middle');
  [1, 2, 3, 4, 5, 6, 14].forEach(function (c) {
    sh.getRange(first, c, ROWS, 1).setBackground(CREAM);
  });
  [7, 8, 9, 10, 11, 12, 13].forEach(function (c) {
    sh.getRange(first, c, ROWS, 1).setBackground(WHITE);
  });
  [3, 4, 6, 7, 9, 10, 11, 12, 13].forEach(function (c) {
    sh.getRange(first, c, ROWS, 1).setFontFamily(NUM);
  });
  sh.getRange(first, 1, ROWS, 1).setNumberFormat('DD.MM.YYYY').setHorizontalAlignment('center');
  sh.getRange(first, 5, ROWS, 1).setNumberFormat('DD.MM.YYYY').setHorizontalAlignment('center');
  sh.getRange(first, 2, ROWS, 1).setHorizontalAlignment('center').setFontWeight('bold');
  sh.getRange(first, 3, ROWS, 1).setNumberFormat('#,##0.00######');
  sh.getRange(first, 6, ROWS, 1).setNumberFormat('#,##0.00######');
  sh.getRange(first, 9, ROWS, 1).setNumberFormat('#,##0.00######');
  sh.getRange(first, 7, ROWS, 1).setNumberFormat('#,##0.0000####');
  sh.getRange(first, 4, ROWS, 1).setNumberFormat('#,##0.00" $"');
  sh.getRange(first, 10, ROWS, 2).setNumberFormat('#,##0.00" $"');
  sh.getRange(first, 12, ROWS, 1).setNumberFormat('+0.0%;-0.0%');
  sh.getRange(first, 13, ROWS, 1).setNumberFormat('0').setHorizontalAlignment('center');
  sh.getRange(first, 8, ROWS, 1).setHorizontalAlignment('center')
    .setFontFamily(TXT).setFontSize(9).setFontWeight('bold');
  sh.getRange(first, 14, ROWS, 1).setFontFamily(TXT).setFontSize(9)
    .setFontColor(MUTED).setFontStyle('italic');

  // подсветка
  var pnl = sh.getRange(first, 11, ROWS, 2);
  var stat = sh.getRange(first, 8, ROWS, 1);
  var live = sh.getRange(first, 9, ROWS, 6);
  sh.setConditionalFormatRules([
    SpreadsheetApp.newConditionalFormatRule()
      .whenNumberGreaterThan(0).setFontColor(UP).setBold(true).setRanges([pnl]).build(),
    SpreadsheetApp.newConditionalFormatRule()
      .whenNumberLessThan(0).setFontColor(DOWN).setBold(true).setRanges([pnl]).build(),
    SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('Открыт').setBackground('#FFF2D6').setFontColor(WARN)
      .setBold(true).setRanges([stat]).build(),
    SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('Закрыт').setBackground('#E8F0EB').setFontColor(UP)
      .setBold(true).setRanges([stat]).build(),
    SpreadsheetApp.newConditionalFormatRule()
      .whenFormulaSatisfied('=$I' + first + '="НЕТ ЦЕНЫ"')
      .setBackground(ALARM).setFontColor(DOWN).setBold(true).setRanges([live]).build()
  ]);

  var w = [95, 78, 100, 100, 95, 100, 100, 80, 100, 110, 92, 85, 55, 300];
  for (var c = 0; c < w.length; c++) sh.setColumnWidth(c + 1, w[c]);
  sh.getRange(4, 1, ROWS + 1, 14).createFilter();
}

/**
 * Мягкая защита расчётных столбцов G..M: при попытке ввести туда значение
 * Google спросит подтверждение. Формулу больше не затрёшь случайно.
 */
function protectComputed_(sh) {
  var TAG = 'Расчётные столбцы — считаются сами';
  sh.getProtections(SpreadsheetApp.ProtectionType.RANGE).forEach(function (p) {
    if (p.getDescription() === TAG) p.remove();
  });
  sh.getRange(5, 7, ROWS, 7).protect().setDescription(TAG).setWarningOnly(true);
}

/** Формулы столбцов G..M листа «Сделки». Данные не трогает. */
function writeTradeFormulas_(sh) {
  var first = 5, f = [];
  for (var r = first; r < first + ROWS; r++) {
    f.push([
      f_('=IF(OR($C' + r + '="",$D' + r + '=""),"",$D' + r + '/$C' + r + ')'),
      f_('=IF($A' + r + '="","",IF($F' + r + '<>"","Закрыт","Открыт"))'),
      f_('=IF($B' + r + '="","",IF($F' + r + '<>"",$F' + r + ',IFERROR(INDEX(' + SH_PRICES +
         '!$C:$C,MATCH($B' + r + ',' + SH_PRICES + '!$B:$B,0)),"НЕТ ЦЕНЫ")))'),
      f_('=IF(OR($G' + r + '="",NOT(ISNUMBER($I' + r + '))),"",$G' + r + '*$I' + r + ')'),
      f_('=IF($J' + r + '="","",$J' + r + '-$D' + r + ')'),
      f_('=IF(OR($K' + r + '="",$D' + r + '=""),"",$K' + r + '/$D' + r + ')'),
      f_('=IF($A' + r + '="","",IF($E' + r + '<>"",$E' + r + '-$A' + r + ',TODAY()-$A' + r + '))')
    ]);
  }
  sh.getRange(first, 7, ROWS, 7).setFormulas(f);
  try { protectComputed_(sh); } catch (e) {}
}

// ─────────────────── ЛИСТ «ЦЕНЫ» ───────────────────
function buildPrices_(ss) {
  var sh = sheet_(ss, SH_PRICES);
  titleBar_(sh, 4, 'ЦЕНЫ', 'Обновляет скрипт. Вручную ничего не меняй.');

  sh.getRange('A3').setValue('Обновлено:').setFontFamily(TXT).setFontWeight('bold').setFontSize(10);
  sh.getRange('B3').setValue('—').setFontFamily(NUM).setFontSize(10)
    .setNumberFormat('DD.MM.YYYY HH:MM').setHorizontalAlignment('center');
  sh.getRange('C3').setFormula(f_('=IF(B3="—","скрипт ещё не запускался",' +
    'IF(NOW()-B3>0.5,"ЦЕНЫ УСТАРЕЛИ","цены свежие"))'))
    .setFontFamily(TXT).setFontWeight('bold').setFontSize(10).setHorizontalAlignment('center');
  sh.getRange('D3').setValue('источник: —')
    .setFontFamily(TXT).setFontSize(9).setFontColor(MUTED).setFontStyle('italic');
  sh.setRowHeight(3, 24);

  sh.getRange(4, 1, 1, 3).setValues([['Название', 'Символ', 'Цена USD']])
    .setBackground(SLATE).setFontColor(WHITE).setFontFamily(TXT).setFontSize(9)
    .setFontWeight('bold').setHorizontalAlignment('center')
    .setBorder(true, true, true, true, true, true, LINE, null);
  sh.setRowHeight(4, 24);
  sh.setFrozenRows(4);

  var rows = COINS.map(function (c) { return [c[0], c[1], 0]; });
  for (var i = 0; i < 8; i++) rows.push(['', '', '']);   // запас под свои монеты
  sh.getRange(5, 1, rows.length, 3).setValues(rows)
    .setBorder(true, true, true, true, true, true, LINE, null)
    .setFontFamily(TXT).setFontSize(10).setFontColor(INK);
  sh.getRange(5, 2, rows.length, 1).setHorizontalAlignment('center');
  sh.getRange(5, 3, rows.length, 1).setFontFamily(NUM)
    .setNumberFormat('#,##0.00########').setHorizontalAlignment('right');

  sh.setConditionalFormatRules([
    SpreadsheetApp.newConditionalFormatRule()
      .whenFormulaSatisfied(f_('=ISNUMBER(SEARCH("УСТАРЕЛИ",$C$3))'))
      .setBackground(ALARM).setFontColor(DOWN).setBold(true)
      .setRanges([sh.getRange('C3')]).build(),
    SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('цены свежие').setFontColor(UP).setBold(true)
      .setRanges([sh.getRange('C3')]).build()
  ]);
  [200, 100, 140, 260].forEach(function (px, i) { sh.setColumnWidth(i + 1, px); });
}

// ─────────────────── ЛИСТ «ИТОГИ» ───────────────────
function buildTotals_(ss) {
  var sh = sheet_(ss, SH_TOTAL);
  var S = SH_TRADES;
  titleBar_(sh, 4, 'ИТОГИ ПОРТФЕЛЯ',
            'Считается само из листа «Сделки». Открытые позиции — по текущей цене.');

  function sect(row, text) {
    sh.getRange(row, 1, 1, 4).merge().setValue('  ' + text)
      .setFontFamily(TXT).setFontSize(9).setFontWeight('bold').setFontColor(BRONZE)
      .setVerticalAlignment('middle');
    sh.setRowHeight(row, 26);
  }
  function kv(row, label, formula, fmt, big, tint) {
    sh.getRange(row, 1).setValue(label).setFontFamily(TXT)
      .setFontSize(big ? 11 : 10).setFontColor(big ? INK : MUTED)
      .setFontWeight(big ? 'bold' : 'normal').setVerticalAlignment('middle');
    sh.getRange(row, 2).setFormula(f_(formula)).setFontFamily(NUM)
      .setFontSize(big ? 15 : 11).setFontWeight('bold')
      .setNumberFormat(fmt).setHorizontalAlignment('right').setVerticalAlignment('middle');
    sh.getRange(row, 1, 1, 2).setBackground(tint || WHITE)
      .setBorder(true, true, true, true, true, true, LINE, null);
    sh.setRowHeight(row, big ? 30 : 22);
  }
  var M = '#,##0.00" $"', P = '+0.0%;-0.0%', N = '0';

  sect(4, 'ВСЕГО');
  kv(5, 'Вложено',          '=B11+B18', M, true, HERO);
  kv(6, 'Стоимость сейчас', '=B12+B19', M, true, HERO);
  kv(7, 'Прибыль',          '=B6-B5',   M, true, HERO);
  kv(8, 'в процентах',      '=IF(B5=0,"",B7/B5)', P, true, HERO);

  sect(10, 'ОТКРЫТЫЕ ПОЗИЦИИ');
  kv(11, 'Вложено',             '=SUMIF(' + S + '!$H:$H,"Открыт",' + S + '!$D:$D)', M);
  kv(12, 'Стоимость сейчас',    '=SUMIF(' + S + '!$H:$H,"Открыт",' + S + '!$J:$J)', M);
  kv(13, 'Нереализованный P&L', '=B12-B11', M);
  kv(14, 'в процентах',         '=IF(B11=0,"",B13/B11)', P);
  kv(15, 'Позиций открыто',     '=COUNTIF(' + S + '!$H:$H,"Открыт")', N);

  sect(17, 'ЗАКРЫТЫЕ СДЕЛКИ');
  kv(18, 'Вложено',            '=SUMIF(' + S + '!$H:$H,"Закрыт",' + S + '!$D:$D)', M);
  kv(19, 'Получено',           '=SUMIF(' + S + '!$H:$H,"Закрыт",' + S + '!$J:$J)', M);
  kv(20, 'Реализованный P&L',  '=B19-B18', M);
  kv(21, 'в процентах',        '=IF(B18=0,"",B20/B18)', P);
  kv(22, 'Сделок закрыто',     '=COUNTIF(' + S + '!$H:$H,"Закрыт")', N);
  kv(23, 'Из них прибыльных',  '=COUNTIFS(' + S + '!$H:$H,"Закрыт",' + S + '!$K:$K,">0")', N);
  kv(24, 'Winrate',            '=IF(B22=0,"",B23/B22)', '0.0%');

  sect(26, 'ПО МОНЕТАМ · открытые позиции');
  sh.getRange(27, 1, 1, 4).setValues([['Монета', 'Вложено', 'Сейчас', 'P&L']])
    .setBackground(SLATE).setFontColor(WHITE).setFontFamily(TXT).setFontSize(9)
    .setFontWeight('bold').setHorizontalAlignment('center')
    .setBorder(true, true, true, true, true, true, LINE, null);
  sh.setRowHeight(27, 24);

  var uniq = [];
  TRADES.forEach(function (t) { if (uniq.indexOf(t[1]) === -1) uniq.push(t[1]); });
  var n = 14, fx = [], names = [];
  for (var i = 0; i < n; i++) {
    var r = 28 + i;
    names.push([i < uniq.length ? uniq[i] : '']);
    fx.push([
      '=IF($A' + r + '="","",SUMIFS(' + S + '!$D:$D,' + S + '!$B:$B,$A' + r + ',' + S + '!$H:$H,"Открыт"))',
      '=IF($A' + r + '="","",SUMIFS(' + S + '!$J:$J,' + S + '!$B:$B,$A' + r + ',' + S + '!$H:$H,"Открыт"))',
      '=IF(OR($A' + r + '="",$B' + r + '=0),"",$C' + r + '-$B' + r + ')'
    ]);
  }
  sh.getRange(28, 1, n, 1).setValues(names).setBackground(CREAM)
    .setFontFamily(TXT).setFontSize(10).setFontWeight('bold')
    .setHorizontalAlignment('center').setFontColor(INK);
  sh.getRange(28, 2, n, 3).setFormulas(fx.map(function (row) {
      return row.map(f_);
    })).setBackground(WHITE)
    .setFontFamily(NUM).setFontSize(10).setNumberFormat(M).setHorizontalAlignment('right');
  sh.getRange(28, 1, n, 4).setBorder(true, true, true, true, true, true, LINE, null);
  sh.getRange(28 + n, 1, 1, 4).merge()
    .setValue('  ↑ впиши символ монеты — строка посчитается сама')
    .setFontFamily(TXT).setFontSize(9).setFontColor(MUTED).setFontStyle('italic');

  sh.setConditionalFormatRules([
    SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThan(0)
      .setFontColor(UP).setBold(true)
      .setRanges([sh.getRange('B5:B8'), sh.getRange('B13:B14'),
                  sh.getRange('B20:B21'), sh.getRange(28, 4, n, 1)]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenNumberLessThan(0)
      .setFontColor(DOWN).setBold(true)
      .setRanges([sh.getRange('B5:B8'), sh.getRange('B13:B14'),
                  sh.getRange('B20:B21'), sh.getRange(28, 4, n, 1)]).build()
  ]);
  [230, 150, 130, 130].forEach(function (px, i) { sh.setColumnWidth(i + 1, px); });
}

// ─────────────────── ВЫПАДАЮЩИЙ СПИСОК ───────────────────
function setupDropdown_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var p = ss.getSheetByName(SH_PRICES), t = ss.getSheetByName(SH_TRADES);
  if (!p || !t) return;
  var last = p.getLastRow();
  if (last < 5) return;
  var rule = SpreadsheetApp.newDataValidation()
    .requireValueInRange(p.getRange(5, 2, last - 4, 1), true)
    .setAllowInvalid(false)
    .setHelpText('Выбери монету из списка — иначе цена не подтянется')
    .build();
  t.getRange(5, 2, ROWS, 1).setDataValidation(rule);
}

function setupDropdown() { setupDropdown_(); }

/**
 * Переписывает только формулы, ничего не стирая.
 * Нужно, если формулы показывают #ERROR! из-за разделителя аргументов.
 */
function repairFormulas() {
  var ss = SpreadsheetApp.getActive();
  detectSep_(ss);
  var t = ss.getSheetByName(SH_TRADES);
  if (t) {
    writeTradeFormulas_(t);
    t.getRange(4, 9).setValue('Цена\nрасчёта');
    t.getRange(2, 1).setValue(
      '   Кремовые столбцы заполняешь ты. Белые считаются сами. ' +
      '«Цена расчёта»: пока сделка открыта — текущая цена с листа «Цены», ' +
      'после ввода цены продажи — она же, чтобы результат закрытой сделки больше не менялся.');
  }
  var p = ss.getSheetByName(SH_PRICES);
  if (p) p.getRange('C3').setFormula(f_('=IF(B3="—","скрипт ещё не запускался",' +
    'IF(NOW()-B3>0.5,"ЦЕНЫ УСТАРЕЛИ","цены свежие"))'));
  var it = ss.getSheetByName(SH_TOTAL);
  if (it) buildTotals_(ss);          // лист «Итоги» только считает, данных в нём нет
  SpreadsheetApp.flush();
  ss.toast('Формулы восстановлены во всех строках. Разделитель: "' + SEP +
           '". Расчётные столбцы защищены от случайного ввода.', 'Готово', 8);
}

// ─────────────────── ЦЕНЫ: три источника ───────────────────
function fetchJson_(url) {
  var r = UrlFetchApp.fetch(url, {muteHttpExceptions: true,
    headers: {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}});
  if (r.getResponseCode() !== 200) throw new Error('HTTP ' + r.getResponseCode());
  return JSON.parse(r.getContentText());
}

function srcCoinGecko_() {
  var out = {};
  for (var page = 1; page <= 2; page++) {
    fetchJson_('https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd' +
               '&order=market_cap_desc&per_page=250&page=' + page).forEach(function (x) {
      var s = String(x.symbol).toUpperCase();
      if (x.current_price && out[s] === undefined) out[s] = x.current_price;
    });
  }
  return out;
}
function srcOkx_() {
  var out = {};
  fetchJson_('https://www.okx.com/api/v5/market/tickers?instType=SPOT')
    .data.forEach(function (t) {
      if (t.instId.slice(-5) === '-USDT') out[t.instId.slice(0, -5)] = parseFloat(t.last);
    });
  return out;
}
function srcCoinbase_() {
  var rates = fetchJson_('https://api.coinbase.com/v2/exchange-rates?currency=USD').data.rates;
  var out = {};
  for (var k in rates) {
    var v = parseFloat(rates[k]);
    if (v > 0) out[k.toUpperCase()] = 1 / v;
  }
  return out;
}

function updatePrices() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(SH_PRICES);
  if (!sh) throw new Error('Нет листа «' + SH_PRICES + '» — запусти setup');
  var last = sh.getLastRow();
  if (last < 5) return;
  var symbols = sh.getRange(5, 2, last - 4, 1).getValues();

  // Binance не используется: с серверов Google отвечает 451 (гео-блокировка)
  var sources = [{name: 'Coinbase', fn: srcCoinbase_},
                 {name: 'OKX', fn: srcOkx_},
                 {name: 'CoinGecko', fn: srcCoinGecko_}];
  var map = {}, used = [], failed = [];
  sources.forEach(function (s) {
    try {
      var m = s.fn(), n = 0;
      for (var k in m) { map[k] = m[k]; n++; }
      if (n) used.push(s.name);
    } catch (e) { failed.push(s.name + ' (' + e.message + ')'); }
  });
  if (!used.length) throw new Error('Ни один источник цен недоступен: ' + failed.join(', '));
  if (map['USDT'] === undefined) map['USDT'] = 1;

  var out = [], found = 0, total = 0;
  symbols.forEach(function (row) {
    var s = String(row[0]).trim().toUpperCase();
    if (!s) { out.push(['']); return; }
    total++;
    if (map[s] !== undefined) { out.push([map[s]]); found++; }
    else out.push(['#НЕТ ЦЕНЫ']);
  });
  sh.getRange(5, 3, out.length, 1).setValues(out);
  sh.getRange('B3').setValue(new Date());
  sh.getRange('D3').setValue('источник: ' + used.join(' + ') +
    (failed.length ? '   ·   недоступны: ' + failed.join(', ') : ''));
  try { setupDropdown_(ss); } catch (e) {}
  ss.toast('Обновлено ' + found + ' из ' + total + ' монет · ' + used.join(', '), 'Цены', 6);
}

function installTrigger() {
  removeTriggers();
  ScriptApp.newTrigger('updatePrices').timeBased().everyHours(1).create();
  SpreadsheetApp.getUi().alert('Готово — цены будут обновляться каждый час.');
}
function removeTriggers() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'updatePrices') ScriptApp.deleteTrigger(t);
  });
}
