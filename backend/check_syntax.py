import py_compile

files = [
    'app/bot/handlers.py',
    'app/services/notification.py',
]

for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"{f}: OK")
    except py_compile.PyCompileError as e:
        print(f"{f}: ERROR -> {e}")

