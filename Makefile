init:
	pip install -r requirements.txt
	npm ci
	ape plugins install .

test:
	ape test -s
	ape test --network :mainnet-fork:hardhat -s
