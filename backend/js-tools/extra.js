const espree = require("espree");
const fs = require("fs");

const code = fs.readFileSync(0, "utf8");

let ast;
try {
  ast = espree.parse(code, { ecmaVersion: 2022, sourceType: "module", loc: true });
} catch (e1) {
  try {
    ast = espree.parse(code, { ecmaVersion: 2022, sourceType: "script", loc: true });
  } catch (e2) {
    console.log("[]");
    process.exit(0);
  }
}

const LOOPS = new Set(["ForStatement", "ForInStatement", "ForOfStatement", "WhileStatement", "DoWhileStatement"]);
const LOOKUPS = new Set(["indexOf", "includes", "find", "findIndex"]);
const findings = [];

function walk(node, loopDepth) {
  if (!node || typeof node.type !== "string") return;
  let depth = loopDepth;

  if (LOOPS.has(node.type)) {
    depth += 1;
    if (depth === 2) findings.push({ kind: "nested-loop", line: node.loc.start.line });
  }

  if (
    node.type === "CallExpression" &&
    loopDepth > 0 &&
    node.callee.type === "MemberExpression" &&
    node.callee.property &&
    LOOKUPS.has(node.callee.property.name)
  ) {
    findings.push({ kind: "lookup-in-loop", line: node.loc.start.line, method: node.callee.property.name });
  }

  for (const key of Object.keys(node)) {
    if (key === "loc" || key === "range") continue;
    const v = node[key];
    if (Array.isArray(v)) v.forEach(c => walk(c, depth));
    else if (v && typeof v.type === "string") walk(v, depth);
  }
}

walk(ast, 0);
console.log(JSON.stringify(findings));