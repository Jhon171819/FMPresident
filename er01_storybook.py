"""Catálogo offline da ER-01. Nenhum comando abre processos ou agenda execução."""
import copy
import json
import re
import time
from pathlib import Path
from er01 import ROOT, canonical, digest

STATES = {'UNMAPPED','HYPOTHESIS','OBSERVED','PARTIAL','VERIFIED','REFUTED','INCONCLUSIVE','DEPRECATED'}
# Grupo, recomendação, custo estimado (não medido).
BLOCKERS = {
    'UNKNOWN_OBJECT_LAYOUT': ('Inferência de tipos','Comparar layouts e ajustes de subobjetos com proveniência por build.','médio'),
    'UNRESOLVED_VIRTUAL_CALL': ('Cobertura de análise','Resolver destinos virtuais apenas com vtable e tipo demonstrados.','alto'),
    'UNRESOLVED_STRING': ('Strings','Classificar representação e propriedade do texto em amostras dirigidas.','médio'),
    'MISSING_UID': ('Qualidade das evidências','Confrontar identificador candidato com fonte independente.','alto'),
    'UNVERIFIED_POINTER_CHAIN': ('Metadados','Registrar segmentos e referências cruzadas sem unir lacunas por inferência.','médio'),
    'INSUFFICIENT_SAMPLES': ('Observações dinâmicas','Repetir amostras limitadas com validação visual e contexto explícito.','baixo'),
    'PARTIAL_GRAPH': ('Grafos','Investigar retomada dentro da função, preservando fronteira e parâmetros.','alto'),
    'DYNAMIC_OBJECT_LIFETIME': ('Cache','Invalidar observações ao mudar processo, época ou âncoras.','médio'),
    'EXPENSIVE_SCAN': ('Performance','Preferir caminhos tipados já conhecidos e medir orçamento por fase.','médio'),
}
TEXT_FIELDS = ('id','title','category','build','object','functional_description','observed_behavior','hypothesis','status')
LIST_FIELDS = ('evidence','unknowns','dependencies','next_experiments','sources','blockers','known_offsets','rvas')


class Storybook:
    def __init__(self, store):
        self.store, self.db = store, store.db
        with self.db:
            self.db.executescript('''
            CREATE TABLE IF NOT EXISTS storybook_meta(version INTEGER NOT NULL);
            INSERT INTO storybook_meta SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM storybook_meta);
            CREATE TABLE IF NOT EXISTS stories(
              id TEXT,build TEXT,object TEXT,category TEXT,status TEXT,equivalence TEXT,body TEXT,revision INTEGER,
              PRIMARY KEY(id,build),UNIQUE(build,equivalence));
            CREATE INDEX IF NOT EXISTS story_object ON stories(object COLLATE NOCASE,build);
            CREATE INDEX IF NOT EXISTS story_category ON stories(category,build,status);
            CREATE INDEX IF NOT EXISTS story_state ON stories(status,build);
            CREATE VIRTUAL TABLE IF NOT EXISTS story_search USING fts5(id UNINDEXED,build UNINDEXED,body);
            CREATE TABLE IF NOT EXISTS story_history(
              id TEXT,build TEXT,revision INTEGER,previous_status TEXT,new_status TEXT,reason TEXT,evidence TEXT,
              timestamp REAL,tool TEXT,context TEXT,body TEXT,
              PRIMARY KEY(id,build,revision),FOREIGN KEY(id,build) REFERENCES stories(id,build));
            ''')
        version=self.db.execute('SELECT version FROM storybook_meta').fetchone()[0]
        if version not in (1,2):
            raise ValueError('Versão do Storybook não suportada')
        if version==1:
            # Índice derivado: pode ser reconstruído sem tocar corpos ou histórico.
            with self.db:
                self.db.execute('DELETE FROM story_search')
                self.db.execute('INSERT INTO story_search(rowid,id,build,body) SELECT rowid,id,build,body FROM stories')
                self.db.execute('UPDATE storybook_meta SET version=2')

    @staticmethod
    def validate(body):
        if not isinstance(body,dict): raise ValueError('História deve ser objeto')
        for key in TEXT_FIELDS:
            if not isinstance(body.get(key),str) or not body[key].strip(): raise ValueError('Campo obrigatório: '+key)
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,99}',body['id']): raise ValueError('ID inseguro')
        if body['status'] not in STATES: raise ValueError('Estado inválido')
        for key in LIST_FIELDS:
            if not isinstance(body.get(key),list): raise ValueError('Lista obrigatória: '+key)
        if not isinstance(body.get('cost'),dict): raise ValueError('Custo deve explicitar medições ou ausência delas')
        if any(not isinstance(x,str) or x not in BLOCKERS for x in body['blockers']): raise ValueError('Bloqueador desconhecido')
        for key in ('unknowns','dependencies','next_experiments','known_offsets','rvas'):
            if any(not isinstance(x,str) or not x.strip() for x in body[key]): raise ValueError('Item inválido: '+key)
        if not body['sources'] or not body['evidence']: raise ValueError('Fonte e evidência obrigatórias')
        for source in body['sources']:
            if not isinstance(source,dict) or not isinstance(source.get('path'),str) or not source['path'].strip() or not isinstance(source.get('sha256'),str) or not re.fullmatch('[a-fA-F0-9]{64}',source['sha256']): raise ValueError('Fonte sem proveniência')
        for ev in body['evidence']:
            if not isinstance(ev,dict) or not ev.get('description') or ev.get('status') not in STATES or not ev.get('source'):
                raise ValueError('Evidência sem descrição, estado ou fonte')
        paths={x['path'] for x in body['sources']}
        if any(x['source'] not in paths for x in body['evidence']): raise ValueError('Evidência com fonte não vinculada')
        if body['status']=='VERIFIED' and not (isinstance(body.get('verified_scope'),str) and body['verified_scope'].strip() and any(e['status']=='VERIFIED' for e in body['evidence'])):
            raise ValueError('VERIFIED exige propriedade, escopo e evidência explícitos')

    def put(self, body, *, reason, tool, context):
        body=copy.deepcopy(body)
        body.pop('history',None);body.pop('revision',None);body.pop('applicability',None)
        self.validate(body)
        if not isinstance(reason,str) or not reason.strip() or not isinstance(tool,str) or not tool.strip() or not isinstance(context,dict) or not context: raise ValueError('Mudança exige justificativa, ferramenta e contexto')
        # Equivalência controlada; nunca combina automaticamente textos parecidos.
        equivalence=body.get('equivalence') or digest(canonical([body['object'].casefold(),body['hypothesis'].casefold()]).encode())
        if not isinstance(equivalence,str):raise ValueError('Equivalência deve ser texto')
        payload=canonical(body)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            duplicate=self.db.execute('SELECT id FROM stories WHERE build=? AND equivalence=?',(body['build'],equivalence)).fetchone()
            if duplicate and duplicate['id']!=body['id']: raise ValueError('Hipótese equivalente já registrada: '+duplicate['id'])
            old=self.db.execute('SELECT * FROM stories WHERE id=? AND build=?',(body['id'],body['build'])).fetchone()
            if old and old['body']==payload:
                self.db.commit();return {'id':body['id'],'changed':False,'revision':old['revision']}
            revision=old['revision']+1 if old else 1
            self.db.execute('INSERT INTO stories VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id,build) DO UPDATE SET object=excluded.object,category=excluded.category,status=excluded.status,equivalence=excluded.equivalence,body=excluded.body,revision=excluded.revision',
                (body['id'],body['build'],body['object'],body['category'],body['status'],equivalence,payload,revision))
            self.db.execute('INSERT INTO story_history VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                (body['id'],body['build'],revision,old['status'] if old else None,body['status'],reason,canonical(body['evidence']),time.time(),tool,canonical(context),payload))
            rowid=self.db.execute('SELECT rowid FROM stories WHERE id=? AND build=?',(body['id'],body['build'])).fetchone()[0]
            self.db.execute('DELETE FROM story_search WHERE rowid=?',(rowid,))
            self.db.execute('INSERT INTO story_search(rowid,id,build,body) VALUES (?,?,?,?)',(rowid,body['id'],body['build'],payload))
            self.db.commit()
        except BaseException:
            self.db.rollback();raise
        return {'id':body['id'],'changed':True,'revision':revision}

    def show(self, identifier, build=None, target_build=None):
        rows=self.db.execute('SELECT * FROM stories WHERE id=?'+(' AND build=?' if build else ''),
                             (identifier,build) if build else (identifier,)).fetchall()
        if len(rows)!=1: raise ValueError('História ausente ou ambígua; informe --build')
        row=rows[0];body=json.loads(row['body'])
        history=[]
        for h in self.db.execute('SELECT * FROM story_history WHERE id=? AND build=? ORDER BY revision',(identifier,row['build'])):
            item=dict(h)
            for key in ('evidence','context','body'):item[key]=json.loads(item[key])
            history.append(item)
        return body|{'revision':row['revision'],'history':history,
                     'applicability':'SAME_BUILD' if target_build==row['build'] else ('UNVERIFIED_OTHER_BUILD' if target_build else 'NOT_ASSESSED')}

    def search(self, query='', *, category=None,status=None,build=None,object=None,unmapped=False,limit=100,offset=0):
        if not 1<=limit<=10000 or offset<0: raise ValueError('Paginação inválida')
        clauses=[];args=[]
        for key,value in (('category',category),('status',status),('build',build),('object',object)):
            if value is not None:clauses.append('s.'+key+'=? COLLATE NOCASE');args.append(value)
        if status and status not in STATES:raise ValueError('Estado inválido')
        if unmapped:clauses.append("s.status NOT IN ('VERIFIED','REFUTED','DEPRECATED')")
        if query.strip():
            # Frase literal FTS, sem operadores fornecidos pelo usuário.
            clauses.append('story_search MATCH ?')
            args.append('"'+query.replace('"','""')+'"')
        source='stories s JOIN story_search f ON f.rowid=s.rowid' if query.strip() else 'stories s'
        sql='SELECT s.body,s.revision FROM '+source+(' WHERE '+' AND '.join(clauses) if clauses else '')+' ORDER BY s.id,s.build LIMIT ? OFFSET ?'
        return [json.loads(r['body'])|{'revision':r['revision']} for r in self.db.execute(sql,args+[limit,offset])]

    def all(self, **filters):
        offset=0
        while True:
            rows=self.search(limit=1000,offset=offset,**filters)
            yield from rows
            if len(rows)<1000:break
            offset+=len(rows)

    def opportunities(self, build=None):
        rows=list(self.all(build=build,unmapped=True));counts={}
        for story in rows:
            for blocker in set(story['blockers']):counts.setdefault(blocker,[]).append(story['id'])
        priorities=[dict(blocker=b,count=len(ids),stories=ids,group=BLOCKERS[b][0],recommendation=BLOCKERS[b][1],estimated_cost=BLOCKERS[b][2]) for b,ids in counts.items()]
        priorities.sort(key=lambda x:(-x['count'],x['blocker']))
        measured=[dict(id=s['id'],cost=s['cost']) for s in rows if s['cost'].get('measured')]
        unique={}
        for m in measured:
            key=m['cost'].get('measurement_id',m['id'])
            if key not in unique:unique[key]={'measurement_id':key,'stories':[],'cost':m['cost']}
            unique[key]['stories'].append(m['id'])
        rankings={k:sorted([m for m in unique.values() if isinstance(m['cost'].get(k),(int,float))],key=lambda m:-m['cost'][k]) for k in ('wall_s','cpu_s','bytes','calls','failures')}
        return {'unmapped':[{'id':s['id'],'object':s['object'],'description':s['functional_description']} for s in rows],
                'priorities':priorities,'measurements':measured,'resource_rankings':rankings,
                'limitations':'Frequência mede alcance, não viabilidade. Custos de melhoria são estimativas qualitativas; medições históricas ausentes não são zero.',
                'automation':'Exportação, consultas, validação de esquema e deduplicação são offline. Nenhuma investigação é iniciada automaticamente.'}

    def export(self, folder, build=None):
        if self.db.in_transaction:raise ValueError('Finalize a transação antes de exportar')
        self.db.execute('BEGIN')
        try:return self._export(folder,build)
        finally:self.db.rollback()  # Snapshot SQLite de leitura; não há mutação do catálogo.

    def _export(self, folder, build=None):
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
        stories=list(self.all(build=build));files=[]
        catalog=['# Catálogo gerado do SQLite ER-01','',f'{len(stories)} histórias. Build: {build or "todas"}.','',
                 'Hipóteses e descrições aparentes não constituem homologação. Histórico completo em snapshot.json.','',
                 '| História | Objeto | Categoria | Estado | Revisão |','|---|---|---|---|---|']
        snapshots=[]
        for s in stories:
            name=s['id']+'-'+digest(s['build'].encode())[:12]+'.md'
            full=self.show(s['id'],s['build']);snapshots.append(full)
            catalog.append(f"| [{s['id']}]({name}) | {s['object']} | {s['category']} | {s['status']} | {s['revision']} |")
            lines=[f"# {s['id']} — {s['title']}",'',f"Build: `{s['build']}` · Estado: **{s['status']}** · Revisão: {s['revision']}",'']
            for field,label in (('object','Objeto'),('functional_description','Funcionamento aparente'),('observed_behavior','Observado'),('hypothesis','Hipótese')):
                lines += [f'## {label}','',s[field],'']
            for field,label in (('evidence','Evidências'),('unknowns','Lacunas'),('dependencies','Dependências'),('next_experiments','Próximos experimentos'),('known_offsets','Offsets'),('rvas','RVAs'),('blockers','Bloqueadores'),('sources','Fontes'),('cost','Custo'),('history','Histórico completo')):
                lines += [f'## {label}','','```json',json.dumps(full[field],ensure_ascii=False,indent=2),'```','']
            (folder/name).write_text('\n'.join(lines),encoding='utf8');files.append(name)
        (folder/'catalogo.md').write_text('\n'.join(catalog)+'\n',encoding='utf8')
        (folder/'snapshot.json').write_text(json.dumps(snapshots,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        opportunities=self.opportunities(build)
        lines=['# Oportunidades ER-01 — gerado do Storybook','',opportunities['limitations'],'',
               'Ordenação: número decrescente de histórias abertas beneficiadas; empate por bloqueador.','',
               '| Bloqueador | Histórias | Grupo | Recomendação | Custo estimado |','|---|---|---|---|---|']
        for p in opportunities['priorities']:
            lines.append(f"| {p['blocker']} | {p['count']}: {', '.join(p['stories'])} | {p['group']} | {p['recommendation']} | {p['estimated_cost']} |")
        lines += ['','## Estruturas abertas','']+[f"- {s['id']} — {s['object']}: {s['description']}" for s in opportunities['unmapped']]
        lines += ['','## Recursos e falhas medidos','','Rankings decrescentes, deduplicados por measurement_id. Um lote não é custo isolado de cada função.','','```json',json.dumps(opportunities['resource_rankings'],ensure_ascii=False,indent=2),'```','',
                  'Não há ranking comparável de CPU/erros por método quando as fontes não fornecem essas medições. Valores de uma mesma amostra não devem ser somados entre histórias.','',
                  '## Automação e capacidades ausentes','',opportunities['automation'],'',
                  'Menor custo estimado: amostragem dirigida. Maior alcance: primeiros bloqueadores da tabela. Falta evidência para estimar horas ou garantia de resolução.','',
                  'Categorias sem bloqueador ativo permanecem sem recomendação; nenhuma melhoria é implementada por este relatório.']
        (folder/'ER-01-opportunities.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
        manifest={'schema':2,'build':build,'stories':[{'id':s['id'],'build':s['build'],'revision':s['revision']} for s in stories],
                  'files':{name:digest((folder/name).read_bytes()) for name in files+['catalogo.md','snapshot.json','ER-01-opportunities.md']}}
        (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        return {'stories':len(stories),'folder':str(folder.resolve()),'manifest':manifest}


def seed_stories():
    """Somente fontes históricas; pode ser executado sem FM ou executável instalado."""
    build='23.2.0+1771058'
    base='docs/taticas/'
    specs=[
        ('ST-01','TEAM e coleções','collections','TEAM','PARTIAL',
         'Contém intervalos candidatos de referências a tipos de jogadores; finalidade esportiva não demonstrada.',
         'Três vetores candidatos em +0x38, +0xF0 e +0x1A8, com ACTUAL_PLAYER e outros tipos; não houve interseção dos ACTUAL_PLAYER observados.',
         'As três coleções podem representar grupos diferentes; significado desconhecido.',
         ['0x38','0xF0','0x1A8'],[],['UNKNOWN_OBJECT_LAYOUT','INSUFFICIENT_SAMPLES'],['Semântica de cada coleção'],['ST-03','ST-04'],
         ['Comparar identidades dirigidas e métodos consumidores'],base+'TC-01.1B-colecoes.md'),
        ('ST-02','ACTUAL_PLAYER e TEAM','relations','ACTUAL_PLAYER','PARTIAL',
         'Campos contêm referências a equipes; o vínculo contratual não está demonstrado.',
         'Quatro objetos em TEAM+0x38 apontaram em +0x130 para TEAM de clubes 335, 316, 1181 e 102555. +0x138 também contém referências; correspondência não universal.',
         'A hipótese de +0x130 sempre apontar à equipe da coleção foi refutada; outras semânticas permanecem abertas.',
         ['0x130','0x138'],[],['UNKNOWN_OBJECT_LAYOUT','INSUFFICIENT_SAMPLES'],['Significado das divergências; não presumir empréstimos'],['ST-01','ST-03'],
         ['Confrontar os divergentes com fontes independentes'],base+'TC-01.1B-colecoes.md'),
        ('ST-03','Identidade parcial de Echeverri','player_identity','ACTUAL_PLAYER','PARTIAL',
         'Possível representação de nome e nascimento associada a um objeto de atleta.',
         'Um objeto apresentou Claudio Jeremías Echeverri em UTF-8 após prefixo de quatro bytes via +0x2B8; +0x2B4 decodificou 02/01/2006, compatível com perfil visual.',
         'Os campos podem participar da identidade; um caso não comprova layout universal ou propriedade da string.',
         ['0x2B8','0x2B4'],[],['UNRESOLVED_STRING','INSUFFICIENT_SAMPLES','MISSING_UID'],['Generalização','Propriedade da string','UID e ligação à linha tática','Sessões independentes'],['ST-04','ST-10'],
         ['Comparar amostra limitada em offsets conhecidos'],base+'TC-01.1B-identificacao-atletas.md'),
        ('ST-04','PLAYER e PERSON','classes','PLAYER / PERSON','UNMAPPED',
         'Nomes RTTI sugerem representações de jogador e pessoa; composição e herança precisam de prova.',
         'RTTI contém PLAYER, PERSON, ACTUAL_PERSON, ACTUAL_PERSON_BASE, BASIC_PERSON, CLIENT_PERSON e PERSON_TRANSLATABLE; vbtable de ACTUAL_PLAYER mostrou ajustes -8, 616, 656.',
         'Subobjetos podem explicar campos interpretados com base incorreta.',
         ['0x270','0x298'],[],['UNKNOWN_OBJECT_LAYOUT','UNVERIFIED_POINTER_CHAIN'],['Relação concreta ACTUAL_PLAYER/PLAYER/PERSON'],['ST-03'],
         ['Verificar subobjetos sem impor equivalência pelo nome RTTI'],base+'TC-01.1B-classes.md'),
        ('ST-05','Tabela da interface tática','ui','TACTIC_PLAYER_LIST_TABLE','PARTIAL',
         'Componente de apresentação de jogadores na tática; métodos percorrem intervalo interno, origem dos atletas não demonstrada.',
         'Método slot 47 percorre +0x168/+0x170 e chama 0x2446A00, thunk para 0xDD91CB0.',
         'Registros intermediários podem alimentar linhas; nenhuma linha foi ligada a ACTUAL_PLAYER.',
         ['0x168','0x170'],['0x2446950','0x2446A00','0xDD91CB0'],['UNVERIFIED_POINTER_CHAIN','UNRESOLVED_VIRTUAL_CALL'],['Registro da linha e destino final atleta'],['ST-06','ST-07'],
         ['Consultar grafo existente e chamadas dirigidas'],base+'TC-01.1B-fluxo-dados.md'),
        ('ST-06','Política de recuperação','functions','TACTIC_PLAYER_DATA_RETRIEVAL_POLICY','PARTIAL',
         'Converte e recupera metadados usados pela interface; retorno como identidade de atleta não demonstrado.',
         'Slot 11 chama 0x3A88400/0x3A87F50; +0x38 refere tabela; +0x58 refere CLIENT_TACTIC. Slot 26 consulta propriedade 0x6F626A74.',
         'A política pode intermediar registros e objetos; a cadeia final permanece aberta.',
         ['0x38','0x58'],['0x1DE1130','0x18F0390','0x1DE1490','0x1DE14D0'],['UNVERIFIED_POINTER_CHAIN','UNRESOLVED_VIRTUAL_CALL'],['Retorno concreto e tipos dos metadados'],['ST-05','ST-07','ST-08'],
         ['Aprofundar somente helpers ainda não validados'],base+'TC-01.1B-classes.md'),
        ('ST-07','Metadado 0x64726566','metadata','0x64726566','PARTIAL',
         'Chave usada por rotinas de transformação e busca em registros internos; semântica desconhecida.',
         '0x3A88400 chama virtual +0xB0 e procura a chave em registros de 16 bytes; 0x3A87F50 cria metadado com essa chave. Texto imprimível ferd não identifica atleta.',
         'A chave pode indexar referência, mas não comprova PLAYER/PERSON ou UID.',
         ['0xB0'],['0x3A88400','0x3A87F50'],['UNRESOLVED_VIRTUAL_CALL','UNVERIFIED_POINTER_CHAIN'],['Tipo do payload e destinatário da conversão'],['ST-06'],
         ['Inspecionar helper e tipo de retorno com limite'],base+'TC-01.1B-classes.md'),
        ('ST-08','CLIENT_TACTIC compartilhado','relations','CLIENT_TACTIC','OBSERVED',
         'Objeto compartilhado por componentes da interface de táticas na sessão observada.',
         'Overview+0x1B8, policy+0x58 e quatro botões+0x168 compartilharam referência. Duas leituras; vtables 0x4A57AD8 e secundária 0x4A57DE8.',
         'Pode representar tática exibida/editada; não foi provado que é tática ativa da equipe.',
         ['0x1B8','0x58','0x168'],[],['DYNAMIC_OBJECT_LIFETIME','UNVERIFIED_POINTER_CHAIN'],['Tática ativa versus edição'],['ST-05','ST-06'],
         ['Validar ciclo de vida sem alterar escalação'],base+'TC-01.1B-fluxo-dados.md'),
        ('ST-09','Quatro grafos históricos limitados','engine_limits','CFG legado','PARTIAL',
         'Desmontagem limitada preserva fronteira, mas ainda não explica integralmente estas funções.',
         'Quatro dos 189 grafos históricos bounded. Artefatos legados permanecem LEGACY_UNVERIFIED, sem homologação retroativa.',
         'Aprofundamento dirigido pode recuperar blocos ausentes, com custo e algoritmo explícitos.',
         [],['0x1DE3830','0x1DE1EC0','0x10188C0','0x1011310'],['PARTIAL_GRAPH','EXPENSIVE_SCAN'],['Blocos não visitados','Validade retroativa de versão e parâmetros'],[],
         ['Consultar índice e ampliar só uma função quando sua dependência justificar'],base+'TC-01.1B-classes.md'),
        ('ST-10','UID persistente ausente','player_identity','Identificador do atleta','INCONCLUSIVE',
         'Identificador persistente seria necessário para vincular atletas entre reconstruções; campo ainda desconhecido.',
         'Nome, nascimento, RTTI, referências de equipe e metadados não forneceram UID confrontado com fonte independente; endereço não é identificador persistente.',
         'Método de identidade ou subobjeto PERSON pode fornecer candidato futuro.',
         [],[],['MISSING_UID','UNKNOWN_OBJECT_LAYOUT','INSUFFICIENT_SAMPLES'],['Campo UID','Fonte independente','Persistência entre sessões'],['ST-03','ST-04','ST-07'],
         ['Confrontar candidato tipado com identificador exposto pelo FM; sem reiniciar ou trocar save'],base+'TC-01.1B-identificacao-atletas.md'),
    ]
    for id,title,category,obj,status,functional,observed,hypothesis,offsets,rvas,blockers,unknowns,deps,experiments,path in specs:
        source={'path':path,'sha256':digest((ROOT/path).read_bytes()),'origin':'TC-01.1 / TC-01.1B'}
        yield dict(id=id,title=title,category=category,build=build,object=obj,status=status,
                   functional_description=functional,observed_behavior=observed,hypothesis=hypothesis,
                   known_offsets=offsets,rvas=rvas,blockers=blockers,unknowns=unknowns,dependencies=deps,
                   next_experiments=experiments,sources=[source],cost={'measured':False,'note':'Sem custo isolado comparável na fonte histórica'},
                   evidence=[dict(description=observed,status=status,source=path)])
