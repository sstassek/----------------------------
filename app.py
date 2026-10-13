import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

DB_PATH = "заявки.db"

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Учёт заявок на печать")
        self.root.geometry("950x550")

        # Поиск
        top = tk.Frame(root)
        top.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(top, text="Поиск:").pack(side=tk.LEFT)
        self.search = tk.Entry(top, width=30)
        self.search.pack(side=tk.LEFT, padx=5)
        tk.Button(top, text="Найти", command=self.load).pack(side=tk.LEFT)
        tk.Button(top, text="Сбросить", command=self.reset).pack(side=tk.LEFT, padx=5)
        tk.Button(top, text="Сводка", command=self.summary).pack(side=tk.RIGHT)

        # Таблица
        cols = ("id", "заказчик", "описание", "копий", "тип", "статус", "стоимость", "дата")
        self.tree = ttk.Treeview(root, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=110)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Кнопки
        bottom = tk.Frame(root)
        bottom.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(bottom, text="Добавить", command=self.add).pack(side=tk.LEFT)
        tk.Button(bottom, text="Удалить", command=self.delete).pack(side=tk.LEFT, padx=5)
        tk.Button(bottom, text="Сменить статус", command=self.change_status).pack(side=tk.LEFT, padx=5)

        self.load()

    def conn(self):
        c = sqlite3.connect(DB_PATH)
        c.row_factory = sqlite3.Row
        return c

    def load(self):
        q = """SELECT з.id, з.имя_заказчика, з.описание, з.количество_копий,
                      т.название AS тип, з.статус, з.стоимость, з.дата_создания
               FROM Заявка з JOIN ТипПечати т ON т.id = з.тип_печати_id"""
        p = []
        s = self.search.get().strip()
        if s:
            q += " WHERE з.имя_заказчика LIKE ? OR з.описание LIKE ?"
            p = [f"%{s}%", f"%{s}%"]
        q += " ORDER BY з.id DESC"

        c = self.conn()
        rows = c.execute(q, p).fetchall()
        c.close()

        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in rows:
            self.tree.insert("", tk.END, values=(
                r["id"], r["имя_заказчика"], r["описание"],
                r["количество_копий"], r["тип"], r["статус"],
                f"{r['стоимость']:.2f}", r["дата_создания"]
            ))

    def reset(self):
        self.search.delete(0, tk.END)
        self.load()

    def add(self):
        w = tk.Toplevel(self.root)
        w.title("Новая заявка")
        w.geometry("400x350")

        tk.Label(w, text="Имя заказчика:").pack()
        e_name = tk.Entry(w, width=40); e_name.pack()
        tk.Label(w, text="Описание:").pack()
        e_desc = tk.Entry(w, width=40); e_desc.pack()
        tk.Label(w, text="Количество копий:").pack()
        e_count = tk.Entry(w, width=40); e_count.pack()
        tk.Label(w, text="Тип печати:").pack()

        c = self.conn()
        types = c.execute("SELECT id, название, цена_за_копию FROM ТипПечати").fetchall()
        c.close()
        type_var = tk.StringVar()
        combo = ttk.Combobox(w, textvariable=type_var, state="readonly",
                             values=[f"{t['id']}|{t['название']}|{t['цена_за_копию']}" for t in types])
        combo.pack()
        if types: combo.current(0)

        def save():
            name = e_name.get().strip()
            desc = e_desc.get().strip()
            cnt_str = e_count.get().strip()
            t = type_var.get()

            if not name:
                messagebox.showerror("Ошибка", "Заполните имя заказчика"); return
            if not desc:
                messagebox.showerror("Ошибка", "Заполните описание"); return
            try:
                cnt = int(cnt_str)
                if cnt <= 0: raise ValueError
            except ValueError:
                messagebox.showerror("Ошибка", "Введите число больше 0"); return
            if not t:
                messagebox.showerror("Ошибка", "Выберите тип печати"); return

            tid, tname, price = t.split("|")
            cost = round(cnt * float(price), 2)

            c = self.conn()
            c.execute("""INSERT INTO Заявка
                (имя_заказчика, описание, количество_копий, тип_печати_id, статус, стоимость, дата_создания)
                VALUES (?, ?, ?, ?, 'в очереди', ?, datetime('now'))""",
                (name, desc, cnt, int(tid), cost))
            c.commit(); c.close()
            w.destroy(); self.load()

        tk.Button(w, text="Сохранить", command=save).pack(pady=10)

    def delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Внимание", "Выберите заявку"); return
        if not messagebox.askyesno("Подтверждение", "Удалить выбранную заявку?"): return
        rid = self.tree.item(sel[0])['values'][0]
        c = self.conn()
        c.execute("DELETE FROM Заявка WHERE id = ?", (rid,))
        c.commit(); c.close()
        self.load()

    def change_status(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Внимание", "Выберите заявку"); return
        item = self.tree.item(sel[0])['values']
        rid, current = item[0], item[5]

        w = tk.Toplevel(self.root)
        w.title("Смена статуса")
        w.geometry("320x150")
        tk.Label(w, text=f"Текущий: {current}").pack(pady=10)
        var = tk.StringVar(value=current)
        ttk.Combobox(w, textvariable=var, state="readonly",
                     values=["в очереди", "печатается", "готово"]).pack()

        def apply():
            c = self.conn()
            c.execute("UPDATE Заявка SET статус = ? WHERE id = ?", (var.get(), rid))
            c.commit(); c.close()
            w.destroy(); self.load()

        tk.Button(w, text="Применить", command=apply).pack(pady=10)

    def summary(self):
        c = self.conn()
        rows = c.execute("""SELECT статус, COUNT(*) AS кол, SUM(стоимость) AS сумма
                            FROM Заявка GROUP BY статус""").fetchall()
        total = c.execute("SELECT COUNT(*), SUM(стоимость) FROM Заявка").fetchone()
        c.close()

        text = "Сводка по статусам:\n\n"
        for r in rows:
            text += f"{r['статус']}: {r['кол']} заявок, {r['сумма'] or 0:.2f} руб.\n"
        text += f"\nВсего: {total[0]} заявок, {total[1] or 0:.2f} руб."
        messagebox.showinfo("Сводка", text)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()