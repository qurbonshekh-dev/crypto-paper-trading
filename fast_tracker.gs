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
  ['Monero','XMR'],
  ['LEO Token','LEO'],
  ['Chainlink','LINK'],
  ['WhiteBIT Coin','WBT'],
  ['Cardano','ADA'],
  ['Stellar','XLM'],
  ['Bitcoin Cash','BCH'],
  ['Canton','CC'],
  ['Dai','DAI'],
  ['USD1','USD1'],
  ['Ethena USDe','USDE'],
  ['Litecoin','LTC'],
  ['Gram (prev. Toncoin)','GRAM'],
  ['Global Dollar','USDG'],
  ['Hedera','HBAR'],
  ['Uniswap','UNI'],
  ['Avalanche','AVAX'],
  ['Sui','SUI'],
  ['Shiba Inu','SHIB'],
  ['Cronos','CRO'],
  ['BlackRock USD Institutional Digital Liquidity Fund','BUIDL'],
  ['PayPal USD','PYUSD'],
  ['Circle USYC','USYC'],
  ['Tether Gold','XAUT'],
  ['MemeCore','M'],
  ['NEAR Protocol','NEAR'],
  ['OKB','OKB'],
  ['Ripple USD','RLUSD'],
  ['Bittensor','TAO'],
  ['Ondo US Dollar Yield','USDY'],
  ['Aave','AAVE'],
  ['PAX Gold','PAXG'],
  ['Pump.fun','PUMP'],
  ['Aster','ASTER'],
  ['World Liberty Financial','WLFI'],
  ['Mantle','MNT'],
  ['Ondo','ONDO'],
  ['Sky','SKY'],
  ['Morpho','MORPHO'],
  ['Ethena','ENA'],
  ['Pepe','PEPE'],
  ['USDD','USDD'],
  ['HTX DAO','HTX'],
  ['Polkadot','DOT'],
  ['Worldcoin','WLD'],
  ['Bitget Token','BGB'],
  ['Internet Computer','ICP'],
  ['Falcon USD','USDF'],
  ['BFUSD','BFUSD'],
  ['United Stables','U'],
  ['USDGO','USDGO'],
  ['Spiko Amundi Overnight Swap Fund (EUR)','EURSAFO'],
  ['Ethereum Classic','ETC'],
  ['POL (ex-MATIC)','POL'],
  ['Bitway','BTW'],
  ['Pi Network','PI'],
  ['Blockchain Capital','BCAP'],
  ['KuCoin','KCS'],
  ['Quant','QNT'],
  ['Lighter','LIT'],
  ['Spiko EU T-Bills Money Market Fund','EUTBL'],
  ['Janus Henderson Anemoy Treasury Fund','JTRSY'],
  ['Gate','GT'],
  ['NEXO','NEXO'],
  ['Invesco Short Duration US Government Securities Fund','USTB'],
  ['Venice Token','VVV'],
  ['Algorand','ALGO'],
  ['Cosmos Hub','ATOM'],
  ['JUST','JST'],
  ['Kaspa','KAS'],
  ['Render','RENDER'],
  ['Jupiter','JUP'],
  ['Janus Henderson Anemoy AAA CLO Fund','JAAA'],
  ['GHO','GHO'],
  ['​​Stable','STABLE'],
  ['Official Trump','TRUMP']
];

// ═══════════════════════════════════════════════════════════════
//  ЖУРНАЛ ЧАСТОЙ ТОРГОВЛИ — тейк +1,5% / стоп −1%
//
//  Установка:
//    1. Создай пустую Google Таблицу
//    2. Расширения → Apps Script
//    3. Удали всё, вставь этот файл целиком, сохрани (Ctrl+S)
//    4. Вверху выбери функцию "setup" и нажми «Выполнить», разреши доступ
//
//  Заполняешь 4 кремовые ячейки на вход. Цель, стоп и команда «что делать
//  сейчас» считаются сами по текущей цене.
// ═══════════════════════════════════════════════════════════════

var SH_LOG = 'Сделки', SH_PRICES = 'Цены', SH_SUM = 'Сводка';
var ROWS = 400;                  // при 20 сделках в день хватит на 20 дней

var TP = 0.015;                  // тейк +1,5%
var SL = 0.01;                   // стоп  −1%
var FEE = 0.00075;               // комиссия 0,075% на сторону (тариф с BNB)
var LOT = 10;                    // размер сделки по умолчанию, $

var INK='#16202B', SLATE='#1F2933', BRONZE='#A9762B', CREAM='#FFF8E7',
    WHITE='#FFFFFF', LINE='#E1E7EC', MUTED='#6B7A88',
    UP='#0F7B4F', DOWN='#B03A2E', WARN='#9A6B15', ALARM='#FDE2DE', HERO='#FBFAF6';
var TXT='Roboto', NUM='Roboto Mono';

var SEP = ',';
function detectSep_(ss) {
  var sh = ss.getSheets()[0];
  var probe = sh.getRange(sh.getMaxRows(), sh.getMaxColumns());
  try {
    probe.setFormula('=SUM(1,1)');
    SpreadsheetApp.flush();
    SEP = (probe.getValue() === 2) ? ',' : ';';
  } catch (e) { SEP = ';'; }
  probe.clear();
  return SEP;
}
function f_(s) { return SEP === ',' ? s : s.split(',').join(';'); }

function onOpen() {
  SpreadsheetApp.getUi().createMenu('Журнал')
    .addItem('Обновить цены', 'updatePrices')
    .addSeparator()
    .addItem('Включить автообновление (раз в час)', 'installTrigger')
    .addItem('Выключить автообновление', 'removeTriggers')
    .addSeparator()
    .addItem('Починить формулы', 'repairFormulas')
    .addItem('Пересобрать таблицу — СТИРАЕТ сделки', 'setup')
    .addToUi();
}

function setup() {
  var ss = SpreadsheetApp.getActive();
  detectSep_(ss);
  buildPrices_(ss);
  buildLog_(ss);
  buildSummary_(ss);
  updatePrices();
  setupDropdown_(ss);
  var keep = [SH_LOG, SH_PRICES, SH_SUM];
  ss.getSheets().slice().forEach(function (s) {
    if (keep.indexOf(s.getName()) === -1) { try { ss.deleteSheet(s); } catch (e) {} }
  });
  ss.setActiveSheet(ss.getSheetByName(SH_LOG));
  ss.toast('Готово. Заполняй кремовые столбцы A–D.', 'Журнал собран', 8);
}

function sheet_(ss, name) {
  var sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);
  var f = sh.getFilter(); if (f) f.remove();
  sh.clear();
  sh.clearConditionalFormatRules();
  var all = sh.getRange(1, 1, sh.getMaxRows(), sh.getMaxColumns());
  all.breakApart();
  try { all.setDataValidation(null); } catch (e) {}
  sh.setHiddenGridlines(true);
  return sh;
}

function titleBar_(sh, cols, text, sub) {
  sh.getRange(1, 1, 1, cols).merge().setValue('  ' + text)
    .setBackground(SLATE).setFontColor(WHITE).setFontFamily(TXT)
    .setFontSize(15).setFontWeight('bold').setVerticalAlignment('middle');
  sh.setRowHeight(1, 34);
  if (sub) {
    sh.getRange(2, 1, 1, cols).merge().setValue('   ' + sub)
      .setFontFamily(TXT).setFontSize(9).setFontColor(MUTED).setFontStyle('italic');
    sh.setRowHeight(2, 20);
  }
}

// ─────────────────── ЛИСТ «СДЕЛКИ» ───────────────────
function buildLog_(ss) {
  var sh = sheet_(ss, SH_LOG);
  titleBar_(sh, 15, 'ЖУРНАЛ ЧАСТОЙ ТОРГОВЛИ',
    'Заполняешь только кремовые A–D (и G–H при выходе). Цель +1,5%, стоп −1% и команда ' +
    '«что делать» считаются сами по текущей цене с листа «Цены».');

  var hdr = ['Дата и время\nвхода','Монета','Цена\nвхода','Сумма\n$',
             'Цель\n+1,5%','Стоп\n−1%','Дата и время\nвыхода','Цена\nвыхода',
             'Кол-во','ЧТО ДЕЛАТЬ','Цена\nсейчас','До цели','До стопа',
             'Итог $','Итог %'];
  sh.getRange(4, 1, 1, 15).setValues([hdr])
    .setBackground(SLATE).setFontColor(WHITE).setFontFamily(TXT).setFontSize(9)
    .setFontWeight('bold').setHorizontalAlignment('center')
    .setVerticalAlignment('middle').setWrap(true)
    .setBorder(true, true, true, true, true, true, LINE, null);
  sh.setRowHeight(4, 42);
  sh.setFrozenRows(4);
  sh.setFrozenColumns(2);

  writeLogFormulas_(sh);

  var body = sh.getRange(5, 1, ROWS, 15);
  body.setBorder(true, true, true, true, true, true, LINE, null)
      .setFontFamily(TXT).setFontSize(10).setFontColor(INK).setVerticalAlignment('middle');
  [1,2,3,4,7,8].forEach(function (c) { sh.getRange(5, c, ROWS, 1).setBackground(CREAM); });
  [5,6,9,10,11,12,13,14,15].forEach(function (c) { sh.getRange(5, c, ROWS, 1).setBackground(WHITE); });
  [3,4,5,6,8,9,11,12,13,14,15].forEach(function (c) { sh.getRange(5, c, ROWS, 1).setFontFamily(NUM); });

  sh.getRange(5, 1, ROWS, 1).setNumberFormat('DD.MM HH:mm').setHorizontalAlignment('center');
  sh.getRange(5, 7, ROWS, 1).setNumberFormat('DD.MM HH:mm').setHorizontalAlignment('center');
  sh.getRange(5, 2, ROWS, 1).setHorizontalAlignment('center').setFontWeight('bold');
  [3,5,6,8,11].forEach(function (c) {
    sh.getRange(5, c, ROWS, 1).setNumberFormat('#,##0.00######').setHorizontalAlignment('right');
  });
  sh.getRange(5, 9, ROWS, 1).setNumberFormat('#,##0.0000####').setHorizontalAlignment('right');
  sh.getRange(5, 4, ROWS, 1).setNumberFormat('#,##0.00" $"').setHorizontalAlignment('right');
  sh.getRange(5, 14, ROWS, 1).setNumberFormat('#,##0.000" $"').setHorizontalAlignment('right');
  sh.getRange(5, 15, ROWS, 1).setNumberFormat('+0.00%;-0.00%').setHorizontalAlignment('right');
  sh.getRange(5, 12, ROWS, 2).setNumberFormat('+0.00%;-0.00%').setHorizontalAlignment('right');
  sh.getRange(5, 10, ROWS, 1).setHorizontalAlignment('center')
    .setFontFamily(TXT).setFontSize(10).setFontWeight('bold');

  var act = sh.getRange(5, 10, ROWS, 1);
  sh.setConditionalFormatRules([
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('ФИКСИРУЙ ПРИБЫЛЬ')
      .setBackground('#D6F0E2').setFontColor(UP).setBold(true).setRanges([act]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('СТОП — ПРОДАВАЙ')
      .setBackground(ALARM).setFontColor(DOWN).setBold(true).setRanges([act]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('держим')
      .setFontColor(MUTED).setRanges([act]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('закрыта')
      .setBackground('#EEF1F4').setFontColor(MUTED).setRanges([act]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThan(0)
      .setFontColor(UP).setBold(true)
      .setRanges([sh.getRange(5,14,ROWS,2)]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenNumberLessThan(0)
      .setFontColor(DOWN).setBold(true)
      .setRanges([sh.getRange(5,14,ROWS,2)]).build(),
    SpreadsheetApp.newConditionalFormatRule()
      .whenFormulaSatisfied(f_('=$K5="НЕТ ЦЕНЫ"'))
      .setBackground(ALARM).setFontColor(DOWN).setBold(true)
      .setRanges([sh.getRange(5,10,ROWS,6)]).build()
  ]);

  var w = [105,78,100,80,100,100,105,100,95,150,100,80,80,90,80];
  for (var c = 0; c < w.length; c++) sh.setColumnWidth(c + 1, w[c]);
  sh.getRange(4, 1, ROWS + 1, 15).createFilter();
  try { protectComputed_(sh); } catch (e) {}
}

function writeLogFormulas_(sh) {
  var out = [];
  for (var r = 5; r < 5 + ROWS; r++) {
    out.push([
      // E цель, F стоп
      f_('=IF($C' + r + '="","",$C' + r + '*' + (1 + TP) + ')'),
      f_('=IF($C' + r + '="","",$C' + r + '*' + (1 - SL) + ')')
    ]);
  }
  sh.getRange(5, 5, ROWS, 2).setFormulas(out);

  out = [];
  for (var r = 5; r < 5 + ROWS; r++) {
    out.push([
      // I кол-во
      f_('=IF(OR($C' + r + '="",$D' + r + '=""),"",$D' + r + '*' + (1 - FEE) + '/$C' + r + ')'),
      // J что делать
      f_('=IF($A' + r + '="","",IF($H' + r + '<>"","закрыта",' +
         'IF(NOT(ISNUMBER($K' + r + ')),"НЕТ ЦЕНЫ",' +
         'IF($K' + r + '<=$F' + r + ',"СТОП — ПРОДАВАЙ",' +
         'IF($K' + r + '>=$E' + r + ',"ФИКСИРУЙ ПРИБЫЛЬ","держим")))))'),
      // K цена сейчас (закрыта -> цена выхода)
      f_('=IF($B' + r + '="","",IF($H' + r + '<>"",$H' + r + ',' +
         'IFERROR(INDEX(' + SH_PRICES + '!$C:$C,MATCH($B' + r + ',' + SH_PRICES + '!$B:$B,0)),"НЕТ ЦЕНЫ")))'),
      // L до цели, M до стопа
      f_('=IF(OR($H' + r + '<>"",NOT(ISNUMBER($K' + r + '))),"",$E' + r + '/$K' + r + '-1)'),
      f_('=IF(OR($H' + r + '<>"",NOT(ISNUMBER($K' + r + '))),"",$F' + r + '/$K' + r + '-1)'),
      // N итог $, O итог %
      f_('=IF(OR($I' + r + '="",NOT(ISNUMBER($K' + r + '))),"",$I' + r + '*$K' + r + '*' + (1 - FEE) + '-$D' + r + ')'),
      f_('=IF(OR($N' + r + '="",$D' + r + '=""),"",$N' + r + '/$D' + r + ')')
    ]);
  }
  sh.getRange(5, 9, ROWS, 7).setFormulas(out);
}

function protectComputed_(sh) {
  var TAG = 'Расчётные столбцы — считаются сами';
  sh.getProtections(SpreadsheetApp.ProtectionType.RANGE).forEach(function (p) {
    if (p.getDescription() === TAG) p.remove();
  });
  sh.getRange(5, 5, ROWS, 2).protect().setDescription(TAG).setWarningOnly(true);
  sh.getRange(5, 9, ROWS, 7).protect().setDescription(TAG).setWarningOnly(true);
}

// ─────────────────── ЛИСТ «ЦЕНЫ» ───────────────────
function buildPrices_(ss) {
  var sh = sheet_(ss, SH_PRICES);
  titleBar_(sh, 4, 'ЦЕНЫ', 'Обновляет скрипт. Вручную ничего не меняй.');
  sh.getRange('A3').setValue('Обновлено:').setFontFamily(TXT).setFontWeight('bold').setFontSize(10);
  sh.getRange('B3').setValue('—').setFontFamily(NUM).setFontSize(10)
    .setNumberFormat('DD.MM.YYYY HH:MM').setHorizontalAlignment('center');
  sh.getRange('C3').setFormula(f_('=IF(B3="—","скрипт ещё не запускался",' +
    'IF(NOW()-B3>0.08,"ЦЕНЫ УСТАРЕЛИ","цены свежие"))'))
    .setFontFamily(TXT).setFontWeight('bold').setFontSize(10).setHorizontalAlignment('center');
  sh.getRange('D3').setValue('источник: —')
    .setFontFamily(TXT).setFontSize(9).setFontColor(MUTED).setFontStyle('italic');
  sh.setRowHeight(3, 24);

  sh.getRange(4, 1, 1, 3).setValues([['Название','Символ','Цена USD']])
    .setBackground(SLATE).setFontColor(WHITE).setFontFamily(TXT).setFontSize(9)
    .setFontWeight('bold').setHorizontalAlignment('center')
    .setBorder(true, true, true, true, true, true, LINE, null);
  sh.setRowHeight(4, 24);
  sh.setFrozenRows(4);

  var rows = COINS.map(function (c) { return [c[0], c[1], 0]; });
  for (var i = 0; i < 8; i++) rows.push(['','','']);
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
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('цены свежие')
      .setFontColor(UP).setBold(true).setRanges([sh.getRange('C3')]).build()
  ]);
  [200,100,140,260].forEach(function (px, i) { sh.setColumnWidth(i + 1, px); });
}

// ─────────────────── ЛИСТ «СВОДКА» ───────────────────
function buildSummary_(ss) {
  var sh = sheet_(ss, SH_SUM);
  var L = SH_LOG;
  titleBar_(sh, 3, 'СВОДКА',
            'Считается само. Комиссия учтена в каждой сделке: 0,075% на вход и на выход.');

  function sect(row, text) {
    sh.getRange(row, 1, 1, 3).merge().setValue('  ' + text)
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
  var M = '#,##0.00" $"', P = '+0.00%;-0.00%', N = '0';

  sect(4, 'ИТОГ');
  kv(5, 'Закрытые сделки, прибыль', '=SUMIF(' + L + '!$H:$H,"<>",' + L + '!$N:$N)', M, true, HERO);
  kv(6, 'Отдано комиссий',          '=(COUNTIF(' + L + '!$H:$H,"<>")*2+COUNTIFS(' + L +
                                    '!$A:$A,"<>",' + L + '!$H:$H,""))*' + LOT + '*' + FEE, M, true, HERO);
  kv(7, 'Открытые позиции, P&L',    '=SUMIFS(' + L + '!$N:$N,' + L + '!$A:$A,"<>",' + L + '!$H:$H,"")', M, true, HERO);

  sect(9, 'СДЕЛКИ');
  kv(10, 'Закрыто всего',    '=COUNTIF(' + L + '!$H:$H,"<>")', N);
  kv(11, 'Из них в плюс',    '=COUNTIFS(' + L + '!$H:$H,"<>",' + L + '!$N:$N,">0")', N);
  kv(12, 'Winrate',          '=IF(B10=0,"",B11/B10)', '0.0%');
  kv(13, 'Открыто сейчас',   '=COUNTIFS(' + L + '!$A:$A,"<>",' + L + '!$H:$H,"")', N);
  kv(14, 'Сегодня открыто',  '=COUNTIFS(' + L + '!$A:$A,">="&TODAY(),' + L + '!$A:$A,"<"&TODAY()+1)', N);
  kv(15, 'Порог безубытка',  '=' + (Math.round((SL + 2*FEE) / (SL + TP) * 1e6) / 1e6), '0.0%');

  sect(17, 'ТРЕБУЮТ ДЕЙСТВИЯ');
  kv(18, 'Достигли цели',    '=COUNTIF(' + L + '!$J:$J,"ФИКСИРУЙ ПРИБЫЛЬ")', N);
  kv(19, 'Достигли стопа',   '=COUNTIF(' + L + '!$J:$J,"СТОП — ПРОДАВАЙ")', N);

  sh.setConditionalFormatRules([
    SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThan(0)
      .setFontColor(UP).setBold(true)
      .setRanges([sh.getRange('B5'), sh.getRange('B7')]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenNumberLessThan(0)
      .setFontColor(DOWN).setBold(true)
      .setRanges([sh.getRange('B5'), sh.getRange('B7')]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThan(0)
      .setFontColor(BRONZE).setBold(true).setRanges([sh.getRange('B6')]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThan(0)
      .setBackground('#D6F0E2').setFontColor(UP).setBold(true)
      .setRanges([sh.getRange('B18')]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThan(0)
      .setBackground(ALARM).setFontColor(DOWN).setBold(true)
      .setRanges([sh.getRange('B19')]).build()
  ]);
  [260,150,120].forEach(function (px, i) { sh.setColumnWidth(i + 1, px); });
}

// ─────────────────── СПИСОК МОНЕТ ───────────────────
function setupDropdown_(ss) {
  ss = ss || SpreadsheetApp.getActive();
  var p = ss.getSheetByName(SH_PRICES), t = ss.getSheetByName(SH_LOG);
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

function repairFormulas() {
  var ss = SpreadsheetApp.getActive();
  detectSep_(ss);
  var t = ss.getSheetByName(SH_LOG);
  if (t) { writeLogFormulas_(t); try { protectComputed_(t); } catch (e) {} }
  if (ss.getSheetByName(SH_SUM)) buildSummary_(ss);
  setupDropdown_(ss);
  SpreadsheetApp.flush();
  ss.toast('Формулы восстановлены. Разделитель: "' + SEP + '"', 'Готово', 6);
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
  for (var k in rates) { var v = parseFloat(rates[k]); if (v > 0) out[k.toUpperCase()] = 1 / v; }
  return out;
}

function updatePrices() {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(SH_PRICES);
  if (!sh) throw new Error('Нет листа «' + SH_PRICES + '» — запусти setup');
  var last = sh.getLastRow();
  if (last < 5) return;
  var symbols = sh.getRange(5, 2, last - 4, 1).getValues();

  // Binance не используется: отвечает 451 серверам Google
  var sources = [{name:'Coinbase',fn:srcCoinbase_},{name:'OKX',fn:srcOkx_},
                 {name:'CoinGecko',fn:srcCoinGecko_}];
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
    if (map[s] !== undefined) { out.push([map[s]]); found++; } else out.push(['#НЕТ ЦЕНЫ']);
  });
  sh.getRange(5, 3, out.length, 1).setValues(out);
  sh.getRange('B3').setValue(new Date());
  sh.getRange('D3').setValue('источник: ' + used.join(' + ') +
    (failed.length ? '   ·   недоступны: ' + failed.join(', ') : ''));
  try { setupDropdown_(ss); } catch (e) {}
  ss.toast('Обновлено ' + found + ' из ' + total + ' монет · ' + used.join(', '), 'Цены', 5);
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
