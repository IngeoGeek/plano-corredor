import asyncio, sys, subprocess, time, os
from playwright.async_api import async_playwright
sitio, salida = sys.argv[1], sys.argv[2]; os.makedirs(salida, exist_ok=True)
srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8765', '-d', sitio], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        errores = []
        pg = await b.new_page(viewport={'width': 1440, 'height': 900}, device_scale_factor=1)
        pg.on('pageerror', lambda e: errores.append(str(e))); pg.on('console', lambda m: errores.append('console:' + m.text) if m.type == 'error' else None)
        await pg.goto('http://localhost:8765/index.html?prueba=6.2201,-73.8124', wait_until='networkidle')
        await pg.wait_for_function("document.querySelector('#mv').loaded === true", timeout=90000); await pg.wait_for_timeout(2500)
        await pg.screenshot(path=f'{salida}/01_escritorio.png')
        # Frente: enfocar desde la tabla
        await pg.click('#tabla-frentes tr:nth-child(3)'); await pg.wait_for_timeout(2500); await pg.screenshot(path=f'{salida}/02_frente.png')
        # Medir entre dos puntos
        await pg.evaluate("document.querySelector('#mv').cameraTarget='auto auto auto'; document.querySelector('#mv').cameraOrbit='0deg 35deg auto'"); await pg.wait_for_timeout(2000)
        await pg.click('#btn-medir'); r = await pg.eval_on_selector('#mv', 'e => e.getBoundingClientRect().toJSON()')
        for fx, fy in ((0.42, 0.45), (0.58, 0.58)):
            await pg.mouse.click(r['x'] + r['width'] * fx, r['y'] + r['height'] * fy); await pg.wait_for_timeout(600)
        await pg.wait_for_timeout(800); await pg.screenshot(path=f'{salida}/03_medida.png')
        print('medida:', await pg.text_content('#resultado-medida'))
        await pg.click('#btn-medir')
        # Superficie apagada, vista desde abajo
        await pg.click('#capas .fila-capa:has-text("Superficie del terreno")'); await pg.evaluate("document.querySelector('#mv').cameraOrbit='120deg 75deg auto'"); await pg.wait_for_timeout(2000)
        await pg.screenshot(path=f'{salida}/04_sin_superficie.png')
        # GPS de prueba
        await pg.click('#btn-gps'); await pg.wait_for_timeout(1200); print('gps:', await pg.text_content('#aviso'))
        # 2D
        await pg.click('#m-2d'); await pg.wait_for_timeout(2500); await pg.screenshot(path=f'{salida}/05_plano2d.png')
        # Rótulo completo
        await pg.click('#m-3d'); await pg.wait_for_timeout(1000)
        h = await pg.evaluate("document.querySelector('.rotulo').scrollHeight"); print('alto rótulo', h)
        await pg.eval_on_selector('.rotulo', 'e => e.scrollTop = 520'); await pg.wait_for_timeout(300); await pg.screenshot(path=f'{salida}/06_rotulo_gas.png')
        # Celular
        m = await b.new_page(**p.devices['Pixel 7']); m.on('pageerror', lambda e: errores.append('movil:' + str(e)))
        await m.goto('http://localhost:8765/index.html', wait_until='networkidle'); await m.wait_for_function("document.querySelector('#mv').loaded === true", timeout=90000); await m.wait_for_timeout(2500)
        await m.screenshot(path=f'{salida}/07_celular.png')
        # Anotación
        await pg.click('#btn-anotar'); await pg.wait_for_timeout(1500); await pg.screenshot(path=f'{salida}/08_anotar.png')
        print('errores:', errores[:8])
        await b.close()
try: asyncio.run(main())
finally: srv.terminate()
