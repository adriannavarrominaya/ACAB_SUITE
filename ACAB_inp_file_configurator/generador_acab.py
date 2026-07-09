import tkinter as tk
from tkinter import ttk, messagebox, filedialog

class GeneradorACAB(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Generador de Mallas Temporales ACAB")
        self.geometry("800x850")
        self.configure(padx=20, pady=20)

        # --- Variables de control ---
        self.num_tramos_irr = tk.IntVar(value=1)
        self.num_tramos_cool = tk.IntVar(value=3)
        
        # Listas para guardar las referencias a los widgets dinámicos
        self.irr_entries = []
        self.cool_entries = []

        self.crear_interfaz()

    def crear_interfaz(self):
        # --- Contenedor Principal con Scroll ---
        # Útil por si se seleccionan los 10 tramos máximos
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- SECCIÓN IRRADIACIÓN ---
        lbl_irr = ttk.Label(self.scrollable_frame, text="FASE DE IRRADIACIÓN", font=("Arial", 12, "bold"))
        lbl_irr.grid(row=0, column=0, sticky="w", pady=(0, 10), columnspan=4)

        ttk.Label(self.scrollable_frame, text="Número de tramos (1-10):").grid(row=1, column=0, sticky="w")
        cb_irr = ttk.Combobox(self.scrollable_frame, textvariable=self.num_tramos_irr, values=list(range(1, 11)), width=5, state="readonly")
        cb_irr.grid(row=1, column=1, sticky="w")
        cb_irr.bind("<<ComboboxSelected>>", self.renderizar_tramos)

        self.frame_irr = ttk.Frame(self.scrollable_frame)
        self.frame_irr.grid(row=2, column=0, columnspan=4, sticky="w", pady=10)

        # --- SECCIÓN ENFRIAMIENTO ---
        lbl_cool = ttk.Label(self.scrollable_frame, text="FASE DE ENFRIAMIENTO", font=("Arial", 12, "bold"))
        lbl_cool.grid(row=3, column=0, sticky="w", pady=(20, 10), columnspan=4)

        ttk.Label(self.scrollable_frame, text="Número de tramos (1-10):").grid(row=4, column=0, sticky="w")
        cb_cool = ttk.Combobox(self.scrollable_frame, textvariable=self.num_tramos_cool, values=list(range(1, 11)), width=5, state="readonly")
        cb_cool.grid(row=4, column=1, sticky="w")
        cb_cool.bind("<<ComboboxSelected>>", self.renderizar_tramos)

        self.frame_cool = ttk.Frame(self.scrollable_frame)
        self.frame_cool.grid(row=5, column=0, columnspan=4, sticky="w", pady=10)

        # --- BOTONES DE ACCIÓN ---
        frame_btns = ttk.Frame(self.scrollable_frame)
        frame_btns.grid(row=6, column=0, columnspan=4, pady=20)

        self.btn_generar = ttk.Button(frame_btns, text="Generar Código Fortran", command=self.generar_codigo)
        self.btn_generar.grid(row=0, column=0, padx=10)
        self.btn_exportar = ttk.Button(frame_btns, text="Exportar a .txt", command=self.exportar_txt)
        self.btn_exportar.grid(row=0, column=1, padx=10)

        # --- ÁREA DE TEXTO (OUTPUT) ---
        self.text_output = tk.Text(self.scrollable_frame, height=20, width=85, font=("Courier", 10), bg="#f4f4f4")
        self.text_output.grid(row=7, column=0, columnspan=4, pady=10)

        # Inicializar los tramos visuales
        self.renderizar_tramos()

    def renderizar_tramos(self, event=None):
        """Renderizado dinámico estricto de los bloques de entrada."""
        # Limpiar contenedores
        for widget in self.frame_irr.winfo_children(): widget.destroy()
        for widget in self.frame_cool.winfo_children(): widget.destroy()
        
        self.irr_entries.clear()
        self.cool_entries.clear()

        # Generar inputs de Irradiación
        ttk.Label(self.frame_irr, text="Tiempo Final (horas)", font=("Arial", 9, "italic")).grid(row=0, column=1, padx=10)
        ttk.Label(self.frame_irr, text="Nº de Pasos", font=("Arial", 9, "italic")).grid(row=0, column=2, padx=10)

        for i in range(self.num_tramos_irr.get()):
            ttk.Label(self.frame_irr, text=f"Tramo {i+1}:").grid(row=i+1, column=0, pady=2)
            t_var = tk.StringVar(value="24.0" if i==0 else "")
            p_var = tk.StringVar(value="10" if i==0 else "")
            
            ttk.Entry(self.frame_irr, textvariable=t_var, width=15).grid(row=i+1, column=1, padx=10)
            e_pasos = tk.Entry(self.frame_irr, textvariable=p_var, width=15)
            e_pasos.grid(row=i+1, column=2, padx=10)
            p_var.trace_add('write', self._validar_pasos)
            self.irr_entries.append((t_var, p_var, e_pasos))

        # Generar inputs de Enfriamiento
        ttk.Label(self.frame_cool, text="Tiempo Final (horas)", font=("Arial", 9, "italic")).grid(row=0, column=1, padx=10)
        ttk.Label(self.frame_cool, text="Nº de Pasos", font=("Arial", 9, "italic")).grid(row=0, column=2, padx=10)

        # Valores sugeridos: pasos cortos al inicio (dinámicas isoméricas) y más largos después
        default_cool_t = ["2.0", "40.0", "140.0"]
        default_cool_p = ["10", "10", "10"]

        for i in range(self.num_tramos_cool.get()):
            ttk.Label(self.frame_cool, text=f"Tramo {i+1}:").grid(row=i+1, column=0, pady=2)
            
            val_t = default_cool_t[i] if i < len(default_cool_t) else ""
            val_p = default_cool_p[i] if i < len(default_cool_p) else ""

            t_var = tk.StringVar(value=val_t)
            p_var = tk.StringVar(value=val_p)
            
            ttk.Entry(self.frame_cool, textvariable=t_var, width=15).grid(row=i+1, column=1, padx=10)
            e_pasos = tk.Entry(self.frame_cool, textvariable=p_var, width=15)
            e_pasos.grid(row=i+1, column=2, padx=10)
            p_var.trace_add('write', self._validar_pasos)
            self.cool_entries.append((t_var, p_var, e_pasos))

    def _validar_pasos(self, *args):
        """Valida que el nº de pasos no supere 10; colorea en rojo y bloquea botones si es inválido."""
        hay_error = False
        for _t, p_var, entry in self.irr_entries + self.cool_entries:
            try:
                val = p_var.get()
            except tk.TclError:
                continue
            try:
                n = int(val)
                if n > 10 or n <= 0:
                    entry.config(bg='#ffcccc')
                    hay_error = True
                else:
                    entry.config(bg='white')
            except ValueError:
                if val:
                    entry.config(bg='#ffcccc')
                    hay_error = True
                else:
                    entry.config(bg='white')
            except tk.TclError:
                pass  # widget destruido durante renderizar_tramos
        estado = 'disabled' if hay_error else 'normal'
        if hasattr(self, 'btn_generar'):
            try:
                self.btn_generar.config(state=estado)
            except tk.TclError:
                pass
        if hasattr(self, 'btn_exportar'):
            try:
                self.btn_exportar.config(state=estado)
            except tk.TclError:
                pass

    def calcular_vector_tiempos(self, entradas):
        """Calcula los puntos de tiempo interpolados linealmente para una fase."""
        tiempos = []
        t_actual = 0.0
        
        for t_var, p_var, *_ in entradas:
            try:
                t_fin = float(t_var.get())
                pasos = int(p_var.get())
            except ValueError:
                raise ValueError("Todos los campos de tiempo deben ser números y los pasos enteros.")

            if pasos <= 0 or t_fin <= t_actual:
                raise ValueError("El tiempo debe ser estrictamente creciente y los pasos mayores a 0.")

            salto = (t_fin - t_actual) / pasos
            for i in range(1, pasos + 1):
                tiempos.append(t_actual + i * salto)
            
            t_actual = t_fin
            
        return tiempos

    def formatear_cientifico(self, numero):
        """Aplica el formato exacto que ACAB espera (ej. 1.000E+00)"""
        return "{:.3E}".format(numero).replace('E-0', 'E-').replace('E+0', 'E+')

    def generar_codigo(self):
        """Motor principal que implementa las reglas de agrupamiento de ACAB."""
        self.text_output.delete("1.0", tk.END)
        
        try:
            # 1. Obtener los vectores matemáticos
            tiempos_irr = self.calcular_vector_tiempos(self.irr_entries)
            tiempos_cool = self.calcular_vector_tiempos(self.cool_entries)
            
            # Etiquetar los datos: 1 = Irradiación (Reactor ON), 0 = Enfriamiento (Reactor OFF)
            lista_global = [(t, 1) for t in tiempos_irr] + [(t, 0) for t in tiempos_cool]
            
            if not lista_global:
                return

            # 2. Dividir en fragmentos (chunks) de máximo 10 pasos
            chunks = [lista_global[i:i + 10] for i in range(0, len(lista_global), 10)]
            codigo_final = []

            for idx, chunk in enumerate(chunks):
                # Cabecera
                if idx == 0:
                    codigo_final.append("<Blocks #7,#8  Irradiation and cooling temporal history")
                else:
                    codigo_final.append("<continue")
                
                # Cálculo de variables de la tarjeta de control
                mmn = sum(1 for t, tipo in chunk if tipo == 1)
                mout = len(chunk)
                ngo = 1 if idx < len(chunks) - 1 else 0
                msub = len(chunks[idx - 1]) if idx > 0 else 0

                # Tarjeta de control (IUNIT = 3 indica horas)
                tarjeta = f" {mmn:2d} {mout:2d}   {ngo} {msub:2d}  3 0   1 0   "
                codigo_final.append(tarjeta)
                
                # Formateo de las cuadrículas de tiempo (máximo 5 por línea)
                tiempos = [t for t, tipo in chunk]
                for j in range(0, len(tiempos), 5):
                    fila = tiempos[j:j+5]
                    fila_str = " ".join([self.formatear_cientifico(t) for t in fila])
                    codigo_final.append(" " + fila_str)

            # Escribir en la interfaz
            self.text_output.insert(tk.END, "\n".join(codigo_final))

        except ValueError as e:
            messagebox.showerror("Error de Validación", str(e))

    def exportar_txt(self):
        """Guarda el bloque generado en un archivo de texto plano."""
        contenido = self.text_output.get("1.0", tk.END).strip()
        if not contenido:
            messagebox.showwarning("Advertencia", "No hay código generado para exportar.")
            return
            
        archivo = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")],
            title="Guardar bloque ACAB"
        )
        if archivo:
            with open(archivo, "w", encoding="utf-8") as f:
                f.write(contenido)
            messagebox.showinfo("Éxito", f"Archivo guardado correctamente en:\n{archivo}")


if __name__ == "__main__":
    app = GeneradorACAB()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        pass