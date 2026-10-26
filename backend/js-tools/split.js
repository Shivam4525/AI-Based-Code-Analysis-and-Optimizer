const espree = require("espree");
const fs = require("fs");

const code = fs.readFileSync(0, "utf8");

function parse(sourceType) {
  return espree.parse(code, { ecmaVersion: 2022, sourceType, loc: true, comment: true });
}

let ast;
try {
  ast = parse("module");
} catch (e1) {
  try {
    ast = parse("script");
  } catch (e2) {
    console.log(JSON.stringify({ error: e2.message }));
    process.exit(0);
  }
}

function names(n) {
  if (n.id && n.id.name) return [n.id.name];
  if ((n.type === "ExportNamedDeclaration" || n.type === "ExportDefaultDeclaration") && n.declaration) {
    return names(n.declaration);
  }
  if (n.type === "VariableDeclaration") {
    return n.declarations.filter(d => d.id.type === "Identifier").map(d => d.id.name);
  }
  return [];
}

function funcNames(n) {
  // Only function/class declarations must be preserved — plain var/let/const
  // bindings are allowed to be refactored (e.g. de-globalizing a leaked var).
  if ((n.type === "FunctionDeclaration" || n.type === "ClassDeclaration") && n.id) {
    return [n.id.name];
  }
  if ((n.type === "ExportNamedDeclaration" || n.type === "ExportDefaultDeclaration") && n.declaration) {
    return funcNames(n.declaration);
  }
  return [];
}

const comments = ast.comments || [];
let prevEnd = 0;
const out = [];

for (const node of ast.body) {
  let start = node.loc.start.line;
  // pull leading comments (e.g. JSDoc) into the same section as their function
  for (let i = comments.length - 1; i >= 0; i--) {
    const c = comments[i];
    if (c.loc.start.line <= prevEnd) continue;
    if (c.loc.end.line >= start - 1 && c.loc.end.line <= start) start = c.loc.start.line;
  }
  out.push({ startLine: start, endLine: node.loc.end.line, type: node.type, names: names(node), funcNames: funcNames(node), });
  prevEnd = node.loc.end.line;
}

console.log(JSON.stringify(out));