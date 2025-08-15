run:
	uvicorn main:app --reload
run-nohup:
	nohup /www/wwwroot/hash.idh863.com/hash_fun_python/3309a7a7941818e131b4dfb9a6349914_venv/bin/uvicorn main:app --reload > transfer.log 2>&1 &