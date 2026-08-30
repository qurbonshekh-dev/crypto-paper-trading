// простой статический сервер для проверки dashboard.html
const http = require("http"), fs = require("fs"), path = require("path");
http.createServer((req, res) => {
  const f = path.join(__dirname, req.url === "/" ? "dashboard.html" : req.url.slice(1));
  fs.readFile(f, (e, buf) => {
    if (e) { res.writeHead(404); res.end("nope"); return; }
    res.writeHead(200, {"Content-Type": "text/html; charset=utf-8"});
    res.end(buf);
  });
}).listen(8765, () => console.log("on 8765"));
