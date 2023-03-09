import pytest
import ape
from tests.conftest import ensure_hardhat


#@pytest.mark.skipif(is_not_hard_hat(), reason="Only run when connected to hard hat.")
def test_vitalik_balance(ensure_hardhat):
    assert ape.api.address.Address("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045").balance == 6616341270242955407304

def test_always_good():
    assert True
