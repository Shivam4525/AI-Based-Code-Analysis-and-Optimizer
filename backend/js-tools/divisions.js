const espree = require("espree");

let code = "";

process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => {
    code += chunk;
});

process.stdin.on("end", () => {
    try {
        const ast = espree.parse(code, {
            ecmaVersion: 2022,
            sourceType: "module",
            loc: true
        });

        const divisions = [];

        function visit(node) {
            if (!node || typeof node !== "object") return;

            if (
                node.type === "BinaryExpression" &&
                node.operator === "/"
            ) {
                divisions.push({
                    line: node.loc.start.line,
                    leftType: node.left.type,
                    rightType: node.right.type,
                    rightValue:
                        node.right.type === "Literal"
                            ? node.right.value
                            : null,
                    rightName:
                        node.right.type === "Identifier"
                            ? node.right.name
                            : null
                });
            }

            for (const value of Object.values(node)) {
                if (Array.isArray(value)) {
                    for (const child of value) visit(child);
                } else if (value && typeof value === "object") {
                    visit(value);
                }
            }
        }

        visit(ast);
        console.log(JSON.stringify(divisions));
    } catch (error) {
        console.log(JSON.stringify({
            error: error.message
        }));
        process.exitCode = 1;
    }
});
