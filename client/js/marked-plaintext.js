function PlainTextRenderer (options) {
  this.options = options || {};
  this.whitespaceDelimiter = this.options.spaces ? ' ' : '\n';
  this.showImageText = (typeof this.options !== 'undefined') ? this.options.showImageText : true;
}

PlainTextRenderer.prototype.code = function(code, lang, escaped) {
  return this.whitespaceDelimiter + this.whitespaceDelimiter + code + this.whitespaceDelimiter + this.whitespaceDelimiter;
}
PlainTextRenderer.prototype.blockquote = function(quote) {
  return '\t' + quote + this.whitespaceDelimiter;
}
PlainTextRenderer.prototype.html = function(html) {
  return html;
}
PlainTextRenderer.prototype.heading = function(text, level, raw) {
  return text;
}
PlainTextRenderer.prototype.hr = function() {
  return this.whitespaceDelimiter + this.whitespaceDelimiter;
}
PlainTextRenderer.prototype.list = function(body, ordered) {
  return body;
}
PlainTextRenderer.prototype.listitem = function(text) {
  return '\t' + text + this.whitespaceDelimiter;
}
PlainTextRenderer.prototype.paragraph = function(text) {
  return this.whitespaceDelimiter + text + this.whitespaceDelimiter;
}
PlainTextRenderer.prototype.table = function(header, body) {
  return  this.whitespaceDelimiter + header + this.whitespaceDelimiter + body + this.whitespaceDelimiter;
}
PlainTextRenderer.prototype.tablerow = function(content) {
  return content + this.whitespaceDelimiter;
}
PlainTextRenderer.prototype.tablecell = function(content, flags) {
  return content + '\t';
}
PlainTextRenderer.prototype.strong = function(text) {
  return text;
}
PlainTextRenderer.prototype.em = function(text) {
  return text;
}
PlainTextRenderer.prototype.codespan = function(text) {
  return text;
}
PlainTextRenderer.prototype.br = function() {
  return this.whitespaceDelimiter + this.whitespaceDelimiter;
}
PlainTextRenderer.prototype.del = function(text) {
  return text;
}
PlainTextRenderer.prototype.link = function(href, title, text) {
  return text;
}
PlainTextRenderer.prototype.image = function(href, title, text) {
  return this.showImageText ? text : '';
}
PlainTextRenderer.prototype.text = function(text) {
  return text;
}
