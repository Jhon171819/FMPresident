"""Reproduz comparação real somente leitura; requer FM aberto e candidato conhecido."""
import argparse
from unittest.mock import patch
import fm23,medir_pf011 as profiling
p=argparse.ArgumentParser();p.add_argument('--samples',type=int,default=10);args=p.parse_args()
if not 1<=args.samples<=30:raise SystemExit('Use de 1 a 30 amostras.')
with patch.object(fm23,'process_info',fm23.process_info_powershell):profiling.run('docs/performance/PF-01.2-baseline-10.json',args.samples)
profiling.rows.clear();profiling.run('docs/performance/PF-01.2-depois-10.json',args.samples)
