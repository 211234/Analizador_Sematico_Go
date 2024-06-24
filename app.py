from flask import Flask, request, render_template_string
import re
import ply.lex as lex

app = Flask(__name__)

# Definición de tokens para el analizador léxico
tokens = [
    'KEYWORD', 'ID', 'NUM', 'SYM', 'ERR'
]

t_KEYWORD = r'\b(package|import|func|main|for|if|else|return|fmt|Println)\b'
t_ID = r'\b[a-zA-Z_][a-zA-Z_0-9]*\b'
t_NUM = r'\b\d+\b'
t_SYM = r'[;{}()\[\]=<>!+-/*]'
t_ERR = r'.'

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    print(f"Carácter ilegal '{t.value[0]}'")
    t.lexer.skip(1)

# Plantilla HTML para mostrar resultados
html_template = '''
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
  <style>
                .contenedor {
                    width: 100%;
                    margin: 20px auto;
                    padding: 20px;
                    background-color: #fff;
                }
                h1 {
                    color: #333;
                }
                textarea {
                    width: 100%;
                    height: 200px;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 10px;
                    margin-bottom: 10px;
                    font-size: 16px;
                }
                input[type="submit"] {
                    background-color: #007BFF;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 18px;
                }
                input[type="submit"]:hover {
                    background-color: #0056b3;
                }
                pre {
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    font-size: 16px;
                }
                .error {
                    color: red;
                    font-weight: bold;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }
                th, td {
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: center;
                }
                th {
                    background-color: #f2f2f2;
                    color: #333;
                }
            </style>
  <title>Analizador Go</title>
</head>
<body>
  <div class="container">
    <h1>Analizador Go</h1>
    <form method="post">
      <textarea name="code" rows="10" cols="50">{{ code }}</textarea><br>
      <input type="submit" value="Analizar">
    </form>
    <div>
      <h2>Analizador Léxico</h2>
      <table>
        <tr>
          <th>Tokens</th><th>KEYWORD</th><th>ID</th><th>Números</th><th>Símbolos</th><th>Error</th>
        </tr>
        {% for row in lexical %}
        <tr>
          <td>{{ row[0] }}</td><td>{{ row[1] }}</td><td>{{ row[2] }}</td><td>{{ row[3] }}</td><td>{{ row[4] }}</td><td>{{ row[5] }}</td>
        </tr>
        {% endfor %}
        <tr>
          <td>Total</td><td>{{ total['KEYWORD'] }}</td><td>{{ total['ID'] }}</td><td>{{ total['NUM'] }}</td><td>{{ total['SYM'] }}</td><td>{{ total['ERR'] }}</td>
        </tr>
      </table>
    </div>
    <div>
      <h2>Analizador Sintáctico y Semántico</h2>
      <table>
        <tr>
          <th>Sintáctico</th><th>Semántico</th>
        </tr>
        <tr>
          <td>{{ syntactic }}</td><td>{{ semantic }}</td>
        </tr>
      </table>
    </div>
  </div>
</body>
</html>
'''

def analyze_lexical(code):
    lexer = lex.lex()
    lexer.input(code)
    results = {'KEYWORD': 0, 'ID': 0, 'NUM': 0, 'SYM': 0, 'ERR': 0}
    rows = []
    while True:
        tok = lexer.token()
        if not tok:
            break
        row = [''] * 6
        if tok.type in results:
            results[tok.type] += 1
            row[list(results.keys()).index(tok.type)] = 'x'
        rows.append(row)
    return rows, results

def analyze_syntactic(code):
    errors = []

    # Verificar la estructura básica de un programa Go
    if "package main" not in code:
        errors.append("El código debe contener 'package main'.")
    if "func main()" not in code:
        errors.append("El código debe contener 'func main()'.")

    # Verificar la estructura de bucles y condicionales
    stack = []
    lines = code.split('\n')
    for i, line in enumerate(lines):
        stripped_line = line.strip()
        if stripped_line.endswith('{'):
            stack.append('{')
        elif stripped_line.endswith('}'):
            if not stack:
                errors.append(f"Llave de cierre sin apertura correspondiente en la línea {i + 1}.")
            else:
                stack.pop()

    if stack:
        errors.append("Una o más llaves de apertura no tienen cierre correspondiente.")

    if not errors:
        return "Sintaxis correcta"
    else:
        return " ".join(errors)

def analyze_semantic(code):
    errors = []

    # Verificar el uso correcto de Println
    if "fmt.Println" not in code:
        errors.append("El código debe usar 'fmt.Println' para imprimir.")

    # Verificar consistencia de variables en bucles y condiciones
    variable_pattern = re.compile(r'for\s+(\w+)\s*:=\s*(\d+);\s*\w+\s*<\s*\d+;\s*\w+\+\+')
    variables = {}
    lines = code.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith("for"):
            match = variable_pattern.search(line)
            if match:
                var_init, num_init = match.groups()
                condition_var = re.search(r'for\s+\w+\s*:=\s*\d+;\s*(\w+)\s*<\s*\d+;', line)
                increment_var = re.search(r'for\s+\w+\s*:=\s*\d+;\s*\w+\s*<\s*\d+;\s*(\w+)\+\+', line)
                if condition_var and increment_var:
                    cond_var = condition_var.group(1)
                    incr_var = increment_var.group(1)
                    if var_init != cond_var or var_init != incr_var:
                        errors.append(f"Inconsistencia de variables en la línea: {line}")
            else:
                errors.append(f"Estructura de bucle 'for' incorrecta en la línea: {line}")

    # Verificar que los números sean enteros
    for num in re.findall(r'\b\d+\b', code):
        if not num.isdigit():
            errors.append(f"Error en el tipo de número: {num}. Debe ser un entero.")

    if not errors:
        return "Uso correcto de las estructuras semánticas"
    else:
        return " ".join(errors)

@app.route('/', methods=['GET', 'POST'])
def index():
    code = ''
    lexical_results = []
    total_results = {'KEYWORD': 0, 'ID': 0, 'NUM': 0, 'SYM': 0, 'ERR': 0}
    syntactic_result = ''
    semantic_result = ''
    if request.method == 'POST':
        code = request.form['code']
        lexical_results, total_results = analyze_lexical(code)
        syntactic_result = analyze_syntactic(code)
        semantic_result = analyze_semantic(code)
    return render_template_string(html_template, code=code, lexical=lexical_results, total=total_results, syntactic=syntactic_result, semantic=semantic_result)

if __name__ == '__main__':
    app.run(debug=True)
