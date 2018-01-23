from tkinter import *
from tkinter import messagebox
import psycopg2
from psycopg2.extras import DictCursor


class LabeledEntry(Frame):

    def __init__(self, master, label_text, default_value=None, entry_char=None):
        super().__init__(master)

        Label(self, text=label_text).grid(row=0, column=0)

        self.text_variable = StringVar()

        if default_value is not None:
            self.text_variable.set(default_value)

        Entry(self, textvariable=self.text_variable, show=entry_char).grid(row=0, column=1)

    def get(self):
        return self.text_variable.get()


class ConnectionFrame(LabelFrame):

    def __init__(self, master):
        super().__init__(master, text="Connection info")

        self.master = master

        self.dbname_entry = LabeledEntry(self, 'dbname:')
        self.dbname_entry.grid(row=0, column=0)

        self.host_entry = LabeledEntry(self, 'host:')
        self.host_entry.grid(row=0, column=1)

        self.user_entry = LabeledEntry(self, 'user:')
        self.user_entry.grid(row=0, column=2)

        self.port_entry = LabeledEntry(self, 'port:')
        self.port_entry.grid(row=0, column=3)

        self.password_entry = LabeledEntry(self, 'password:', entry_char='*')
        self.password_entry.grid(row=0, column=4)

        self.connection_indicator = Label(self, text='  ', background='red')
        self.connection_indicator.grid(row=0, padx=6, column=5)

        self.connect_button = Button(self, text='Connect', command=self.connect)
        self.connect_button.grid(row=0, column=6, sticky=W)

        for child in self.winfo_children():
            for childs_child in child.winfo_children():
                childs_child.bind('<Return>', self.connect)
            child.bind('<Return>', self.connect)
        self.bind('<Return>', self.connect)

        self.conn = None
        self.cur = None

    def connect(self, event=None):
        connection_info = self.get()
        try:
            self.conn = psycopg2.connect(
                '''dbname={dbname}
                host={host}
                user={user}
                port={port}
                password={password}
                '''.format(**connection_info))
            self.cur = self.conn.cursor(cursor_factory=DictCursor)
        except Exception as e:
            messagebox.showerror('Connection error', e)
            return
        else:
            self.connection_indicator.config(background='green')
            self.master.confirm_connection()

    def is_connected(self):
        return self.conn is not None and self.cur is not None

    def get_query_colnames(self):
        return [field[0].upper() for field in self.cur.description]

    def execute(self, query):
        try:
            self.cur.execute(query)
        except psycopg2.ProgrammingError:
            messagebox.showerror('Erreur de programmation', "La commande a échoué.")
            self.connect()
        else:
            if 'SELECT' in query.upper():
                colnames = self.get_query_colnames()
                return [colnames] + self.cur.fetchall()
            else:
                messagebox.showinfo('Succès', 'La commande a été exécutée avec succès.')

    def close_connection(self):
        self.cur.close()


    def get_tabnames(self):
        self.cur.execute("""SELECT table_name FROM information_schema.tables
                       WHERE table_schema = 'public' ORDER BY table_name""")
        return self.cur.fetchall()

    def get_colnames(self, table_name):
        try:
            self.cur.execute("SELECT * FROM {} LIMIT 1".format(table_name))
        except psycopg2.ProgrammingError:
            if not table_name:
                table_name = "<Empty>"
            messagebox.showerror('Name error', 'Table "{}" does not exist.'.format(table_name))
        else:
            return self.get_query_colnames()

    def get(self):
        return {
            'dbname': self.dbname_entry.get(),
            'host': self.host_entry.get(),
            'user': self.user_entry.get(),
            'port': self.port_entry.get(),
            'password': self.password_entry.get()
        }


class QueryFrame(LabelFrame):

    def __init__(self, master):
        super().__init__(master, text='Query editor')

        self.columnconfigure(0, weight=1)

        self.query_field = Text(self)
        self.query_field.grid(row=0, column=0, sticky=EW)

    def get(self):
        return self.query_field.get('1.0', 'end')


class ResultsFrame(LabelFrame):

    def __init__(self, master):
        super().__init__(master, text='Results viewer')

        self.columnconfigure(0, weight=1)

        scrollbar = Scrollbar(self)
        scrollbar.grid(row=0, column=1, sticky=NS)

        self.results_field = Listbox(self, justify=LEFT, yscrollcommand=scrollbar.set)
        self.results_field.grid(row=0, column=0, sticky=EW)

        scrollbar.config(command=self.results_field.yview)

    def set(self, data_list):
        # TODO: Refactor and make alignment actually work
        self.results_field.delete(0, END)
        for row in data_list:
            row = ''.join(['{:<20}'.format(str(item).strip('{').strip('}'))[:20] for item in list(row)]) if isinstance(row, list) else row
            self.results_field.insert(END, row)


class SimpleQuery(Tk):

    def __init__(self):
        super().__init__()
        self.title('SimpleQuery')
        self.resizable(0, 0)
        self.wm_iconbitmap('db.ico')
        self.option_readfile('style.txt')

        self.connection_frame = ConnectionFrame(self)
        self.connection_frame.grid(row=0, column=0)
        self.connection_frame.focus()

        self.query_frame = QueryFrame(self)
        self.query_frame.grid(row=1, column=0, sticky=EW)
        self.query_frame.query_field.bind('<Control-Return>', self.run_query)  # TODO: eliminate coupling

        command_frame = Frame(self)

        self.execute_button = Button(command_frame, text='Execute', command=self.run_query)
        self.execute_button.grid(row=0, column=0, sticky=W, padx=6)

        self.get_tabnames_button = Button(command_frame, text='Get table names', command=self.get_tabnames)
        self.get_tabnames_button.grid(row=0, column=1, sticky=W, padx=6)

        self.get_colnames_button = Button(command_frame, text='Get column names', command=self.get_colnames)
        self.get_colnames_button.grid(row=0, column=2, sticky=W, padx=6)

        self.table_name = StringVar()
        self.tabname_entry = Entry(command_frame, textvariable=self.table_name)
        self.tabname_entry.grid(row=0, column=3, sticky=W)

        self.widgets_requiring_connection = (self.execute_button,
                                             self.get_tabnames_button,
                                             self.get_colnames_button,
                                             self.tabname_entry)

        for widget in self.widgets_requiring_connection:
            widget.config(state='disabled')

        command_frame.grid(row=2, column=0, sticky=EW)

        self.results_frame = ResultsFrame(self)
        self.results_frame.grid(row=3, column=0, sticky=EW)

    def confirm_connection(self):
        for widget in self.widgets_requiring_connection:
            widget.config(state='normal')

    def run_query(self, event=None):
        query_text = self.query_frame.get()
        if not query_text.endswith(';'):
            query_text += ';'
        query_data = self.connection_frame.execute(query_text)
        self.results_frame.set(query_data)
        return "break"  # for keybinding, to prevent any further actions

    def get_tabnames(self):
        table_names = self.connection_frame.get_tabnames()
        self.results_frame.set(table_names)

    def get_colnames(self):
        colnames = self.connection_frame.get_colnames(self.table_name.get())
        self.results_frame.set(colnames)

    def quit(self):
        self.connection_frame.close_connection()
        super().quit()


if __name__ == '__main__':
    SimpleQuery().mainloop()