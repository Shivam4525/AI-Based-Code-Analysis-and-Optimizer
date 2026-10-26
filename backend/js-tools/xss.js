const espree = require("espree");
const fs = require("fs");

const code = fs.readFileSync(0, "utf8");
let ast;

try {
  ast = espree.parse(code, {
    ecmaVersion: 2022,
    sourceType: "module",
    loc: true
  });
} catch (e1) {
  try {
    ast = espree.parse(code, {
      ecmaVersion: 2022,
      sourceType: "script",
      loc: true
    });
  } catch (e2) {
    console.log("[]");
    process.exit(0);
  }
}

const findings = [];

function memberName(node) {
  if (!node || node.type !== "MemberExpression") return null;

  if (!node.computed && node.property.type === "Identifier") {
    return node.property.name;
  }

  if (node.computed && node.property.type === "Literal") {
    return node.property.value;
  }

  return null;
}

function walk(node) {
  if (!node || typeof node.type !== "string") return;

  if (
    node.type === "AssignmentExpression" &&
    node.operator === "=" &&
    memberName(node.left) === "innerHTML"
  ) {
    findings.push({
      kind: "innerHTML-assignment",
      line: node.loc.start.line
    });
  }

  if (node.type === "CallExpression") {
    const callee = node.callee;
    const method = memberName(callee);

    if (method === "insertAdjacentHTML") {
      findings.push({
        kind: "insertAdjacentHTML",
        line: node.loc.start.line
      });
    }

    if (
      callee.type === "MemberExpression" &&
      memberName(callee) === "write" &&
      callee.object.type === "Identifier" &&
      callee.object.name === "document"
    ) {
      const args = node.arguments || [];

      // Ignore document.write calls containing only static strings.
      const isStaticStringOnly =
        args.length > 0 &&
        args.every(arg =>
          arg.type === "Literal" && typeof arg.value === "string"
        );

      if (!isStaticStringOnly) {
        findings.push({
          kind: "document-write",
          line: node.loc.start.line
        });
      }
    }
  }

  for (const key of Object.keys(node)) {
    if (key === "loc" || key === "range") continue;

    const value = node[key];

    if (Array.isArray(value)) {
      value.forEach(walk);
    } else if (value && typeof value.type === "string") {
      walk(value);
    }
  }
}

walk(ast);
console.log(JSON.stringify(findings));
