<!DOCTYPE html>
<html>
<head>
<title>Looping Statements</title>
<script language="JavaScript">
document.write("For Loop demo:<br>");
for (i = 0; i < 5; i++) {
text1 = "The number is " + i + "<br>";
document.write(text1);
}
document.write("<br>While Loop demo:<br>");
var i = 0;
while (i < 10) {
text2 = "The number is " + i;
document.write(text2 + "<br>");
i++;
}
document.write("<br>Do-While Loop demo:<br>");
var i = 0;
do {
text3 = "The number is " + i;
document.write(text3 + "<br>");
i++;
} while (i < 10);
</script>
</head>
<body>
</body>
</html>