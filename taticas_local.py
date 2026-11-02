"""Planejamento manual local; nenhum acesso à memória do jogo."""
import json
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QGridLayout

FORMACOES = {
    '4-4-2': (4,4,2), '4-2-3-1': (4,2,3,1), '4-3-3': (4,3,3),
    '4-1-4-1': (4,1,4,1), '3-5-2': (3,5,2), '3-4-3': (3,4,3), '5-3-2': (5,3,2),
}

class CentralTatica(QWidget):
    def __init__(self):
        super().__init__(); self.slots=[]
        root=QVBoxLayout(self)
        label=QLabel('Planejamento local: os dados são informados por você e não são aplicados ao FM.'); label.setWordWrap(True);root.addWidget(label)
        status=QLabel('Elenco e tática do FM: indisponíveis — estruturas ainda não comprovadas. Os nomes abaixo são manuais.');status.setWordWrap(True);root.addWidget(status)
        row=QHBoxLayout(); row.addWidget(QLabel('Formação')); self.formacao=QComboBox();self.formacao.addItems(FORMACOES);row.addWidget(self.formacao);root.addLayout(row)
        self.campo=QGridLayout();root.addLayout(self.campo)
        for i in range(11):
            item=QLineEdit();item.setPlaceholderText('Jogador');self.slots.append(item)
        self.formacao.currentTextChanged.connect(self.organizar);self.organizar()
        root.addWidget(QLabel('Reservas (um nome por campo)'))
        self.reservas=[]; reserves=QGridLayout();root.addLayout(reserves)
        for i in range(9):
            item=QLineEdit();item.setPlaceholderText('Reserva');self.reservas.append(item);reserves.addWidget(item,i//3,i%3)
        row=QHBoxLayout();root.addLayout(row)
        for title,action in [('Salvar plano',self.salvar),('Abrir plano',self.abrir)]:
            button=QPushButton(title);button.clicked.connect(action);row.addWidget(button)
        root.addStretch()

    def organizar(self):
        for slot in self.slots:self.campo.removeWidget(slot)
        self.campo.addWidget(self.slots[0],0,3,1,2,Qt.AlignCenter)
        index=1
        for row,count in enumerate(FORMACOES[self.formacao.currentText()],1):
            for col in range(count):
                self.campo.addWidget(self.slots[index],row,col*2,1,2);index+=1

    def salvar(self):
        names=[x.text().strip() for x in self.slots+self.reservas if x.text().strip()]
        if len({x.casefold() for x in names}) != len(names):
            QMessageBox.warning(self,'Plano inválido','Um jogador aparece mais de uma vez.');return
        path,_=QFileDialog.getSaveFileName(self,'Salvar plano local','','Plano tático JSON (*.json)')
        if path:
            try: Path(path).write_text(json.dumps({'versao':1,'fonte':'informado manualmente','formacao':self.formacao.currentText(),'titulares':[x.text() for x in self.slots],'reservas':[x.text() for x in self.reservas]},ensure_ascii=False,indent=2),encoding='utf-8')
            except OSError as e: QMessageBox.warning(self,'Erro ao salvar',str(e))

    def abrir(self):
        path,_=QFileDialog.getOpenFileName(self,'Abrir plano local','','Plano tático JSON (*.json)')
        if not path:return
        try:
            data=json.loads(Path(path).read_text(encoding='utf-8'))
            if data.get('versao')!=1 or data.get('formacao') not in FORMACOES or len(data.get('titulares',[]))!=11 or len(data.get('reservas',[]))!=9 or any(not isinstance(x,str) for x in data['titulares']+data['reservas']):raise ValueError('Formato de plano inválido')
            self.formacao.setCurrentText(data['formacao'])
            for field,value in zip(self.slots+self.reservas,data['titulares']+data['reservas']):field.setText(value)
        except (OSError,ValueError,TypeError,KeyError) as e:QMessageBox.warning(self,'Erro ao abrir',str(e))
