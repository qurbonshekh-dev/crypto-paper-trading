/**
 * Автообновление цен для трекера сделок.
 *
 * Три независимых источника с подстраховкой: CoinGecko → OKX → Coinbase.
 * Если один недоступен, цены возьмутся из следующего.
 * Binance не используется: он отвечает кодом 451 на запросы с серверов Google.
 *
 * Установка: в ТАБЛИЦЕ выбрать Расширения → Apps Script, вставить этот код,
 * сохранить, нажать «Выполнить», разрешить доступ. Затем обновить страницу
 * таблицы — появится меню «Обновить цены».
 */

var SHEET_NAME = 'Цены';

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Обновить цены')
    .addItem('Обновить сейчас', 'updatePrices')
    .addItem('Восстановить список монет', 'setupDropdown')
    .addItem('Включить автообновление (каждый час)', 'installTrigger')
    .addItem('Выключить автообновление', 'removeTriggers')
    .addToUi();
}

function fetchJson_(url) {
  var r = UrlFetchApp.fetch(url, {
    muteHttpExceptions: true,
    headers: {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
  });
  if (r.getResponseCode() !== 200) {
    throw new Error('HTTP ' + r.getResponseCode());
  }
  return JSON.parse(r.getContentText());
}

/** CoinGecko — агрегатор, самое широкое покрытие. */
function srcCoinGecko_() {
  var out = {};
  for (var page = 1; page <= 2; page++) {
    var d = fetchJson_('https://api.coingecko.com/api/v3/coins/markets' +
      '?vs_currency=usd&order=market_cap_desc&per_page=250&page=' + page);
    d.forEach(function (x) {
      var s = String(x.symbol).toUpperCase();
      if (x.current_price && out[s] === undefined) out[s] = x.current_price;
    });
  }
  return out;
}

/** OKX — спотовые пары к USDT. */
function srcOkx_() {
  var out = {};
  fetchJson_('https://www.okx.com/api/v5/market/tickers?instType=SPOT')
    .data.forEach(function (t) {
      if (t.instId.slice(-5) === '-USDT') out[t.instId.slice(0, -5)] = parseFloat(t.last);
    });
  return out;
}

/** Coinbase — все курсы одним запросом. */
function srcCoinbase_() {
  var rates = fetchJson_('https://api.coinbase.com/v2/exchange-rates?currency=USD').data.rates;
  var out = {};
  for (var k in rates) {
    var v = parseFloat(rates[k]);
    if (v > 0) out[k.toUpperCase()] = 1 / v;   // курс обратный: 1 USD = v монет
  }
  return out;
}

function updatePrices() {
  var sh = SpreadsheetApp.getActive().getSheetByName(SHEET_NAME);
  if (!sh) throw new Error('Нет листа «' + SHEET_NAME + '»');

  var last = sh.getLastRow();
  if (last < 5) return;
  var symbols = sh.getRange(5, 2, last - 4, 1).getValues();

  // от запасных к основному: следующий источник уточняет цену предыдущего
  var sources = [
    {name: 'Coinbase',  fn: srcCoinbase_},
    {name: 'OKX',       fn: srcOkx_},
    {name: 'CoinGecko', fn: srcCoinGecko_}
  ];
  var map = {}, used = [], failed = [];
  sources.forEach(function (s) {
    try {
      var m = s.fn();
      var n = 0;
      for (var k in m) { map[k] = m[k]; n++; }
      if (n) used.push(s.name);
    } catch (e) {
      failed.push(s.name + ' (' + e.message + ')');
    }
  });
  map['USDT'] = map['USDT'] || 1;

  if (!used.length) {
    throw new Error('Ни один источник цен недоступен: ' + failed.join(', '));
  }

  var out = [], found = 0;
  symbols.forEach(function (row) {
    var s = String(row[0]).trim().toUpperCase();
    if (!s) { out.push(['']); return; }
    if (map[s] !== undefined) { out.push([map[s]]); found++; }
    else { out.push(['#НЕТ ЦЕНЫ']); }
  });

  sh.getRange(5, 3, out.length, 1).setValues(out);
  sh.getRange('B3').setValue(new Date());
  sh.getRange('D3').setValue('источник: ' + used.join(' + ') +
                             (failed.length ? '   недоступны: ' + failed.join(', ') : ''));
  try { setupDropdown(); } catch (e) {}

  SpreadsheetApp.getActive().toast(
    'Обновлено ' + found + ' из ' + out.filter(function (r) { return r[0] !== ''; }).length +
    ' монет · ' + used.join(', '), 'Цены', 6);
}

/**
 * Ставит выпадающий список монет в столбец «Монета» листа «Сделки».
 * Диапазон берётся из листа «Цены», поэтому список всегда совпадает с тем,
 * для чего реально есть цена. Вызывается сам после каждого обновления цен.
 */
function setupDropdown() {
  var ss = SpreadsheetApp.getActive();
  var prices = ss.getSheetByName(SHEET_NAME);
  var trades = ss.getSheetByName('Сделки');
  if (!prices || !trades) return;

  var last = prices.getLastRow();
  if (last < 5) return;
  var src = prices.getRange(5, 2, last - 4, 1);

  var rule = SpreadsheetApp.newDataValidation()
    .requireValueInRange(src, true)          // true = показывать стрелку списка
    .setAllowInvalid(false)
    .setHelpText('Выбери монету из списка на листе «Цены» — иначе цена не подтянется')
    .build();

  trades.getRange(5, 2, trades.getMaxRows() - 4, 1).setDataValidation(rule);
}

function installTrigger() {
  removeTriggers();
  ScriptApp.newTrigger('updatePrices').timeBased().everyHours(1).create();
  SpreadsheetApp.getUi().alert('Готово — цены будут обновляться каждый час автоматически.');
}

function removeTriggers() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'updatePrices') ScriptApp.deleteTrigger(t);
  });
}
