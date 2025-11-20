import yaml
import requests
from loguru import logger


# 加载配置文件
with open("config/config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

ETHERSCAN_API_KEY = config["etherscan"]["api_key"]
ETHERSCAN_API_URL = config["etherscan"]["api_url"]


def get_gas_fee_by_tx_id(tx_hash: str) -> dict:
    """
    根据交易ID（TxHash）查询Gas开销
    """
    if not tx_hash.startswith("0x"):
        tx_hash = "0x" + tx_hash
    
    # 使用 Etherscan V2 API 获取交易收据
    params = {
        "chainid": "1",
        "module": "proxy",
        "action": "eth_getTransactionReceipt",
        "txhash": tx_hash,
        "apikey": ETHERSCAN_API_KEY
    }
    
    try:
        response = requests.get(ETHERSCAN_API_URL, params=params, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        # 处理 JSON-RPC 2.0 格式的响应
        if "error" in result:
            error_msg = result["error"].get("message", "未知错误")
            logger.error(f"Etherscan API 返回错误: {error_msg}")
            return None
        
        if "result" not in result:
            logger.error(f"Etherscan API 响应格式错误: {result}")
            return None
        
        receipt = result["result"]
        
        if receipt is None:
            logger.warning(f"交易 {tx_hash} 不存在或尚未被打包")
            return None
        
        if not isinstance(receipt, dict):
            logger.error(f"交易收据格式错误: {receipt}")
            return None
        
        # 提取Gas相关信息
        gas_used = int(receipt.get("gasUsed", "0x0"), 16)
        
        # 优先使用 effectiveGasPrice（EIP-1559交易），否则使用 gasPrice
        gas_price = 0
        effective_gas_price = None
        if "effectiveGasPrice" in receipt and receipt["effectiveGasPrice"]:
            effective_gas_price = int(receipt["effectiveGasPrice"], 16)
            gas_price = effective_gas_price
        elif "gasPrice" in receipt and receipt["gasPrice"]:
            gas_price = int(receipt["gasPrice"], 16)
        else:
            logger.warning(f"交易 {tx_hash} 没有Gas价格信息")
            return None
        
        # 计算总Gas费用
        total_gas_fee_wei = gas_used * gas_price
        
        # 转换为ETH（1 ETH = 10^18 Wei）
        total_gas_fee_eth = total_gas_fee_wei / 1e18
        
        # 转换为Gwei（1 Gwei = 10^9 Wei）
        gas_price_gwei = gas_price / 1e9
        
        # 获取交易状态
        status = int(receipt.get("status", "0x0"), 16)
        
        # 获取区块号
        block_number = int(receipt.get("blockNumber", "0x0"), 16)
        
        result_dict = {
            "tx_hash": tx_hash,
            "gas_used": gas_used,
            "gas_price": gas_price,
            "gas_price_gwei": round(gas_price_gwei, 2),
            "total_gas_fee_wei": total_gas_fee_wei,
            "total_gas_fee_eth": round(total_gas_fee_eth, 8),
            "status": status,
            "status_text": "成功" if status == 1 else "失败",
            "block_number": block_number,
        }
        
        if effective_gas_price:
            result_dict["effective_gas_price"] = effective_gas_price
            result_dict["effective_gas_price_gwei"] = round(effective_gas_price / 1e9, 2)
        
        logger.info(f"成功查询交易 {tx_hash} 的Gas费用: {result_dict['total_gas_fee_eth']} ETH")
        return result_dict
        
    except requests.exceptions.RequestException as e:
        logger.error(f"请求Etherscan API时发生错误: {e}")
        return None
    except (ValueError, KeyError) as e:
        logger.error(f"解析交易数据时发生错误: {e}")
        return None
    except Exception as e:
        logger.error(f"查询Gas费用时发生未知错误: {e}")
        return None


def get_gas_fee_batch(tx_hashes: list) -> list:
    """
    批量查询多个交易的Gas费用
    
    参数:
        tx_hashes: 交易哈希列表
    
    返回:
        list: 包含每个交易Gas费用信息的字典列表
    """
    results = []
    for tx_hash in tx_hashes:
        result = get_gas_fee_by_tx_id(tx_hash)
        if result:
            results.append(result)
    return results


if __name__ == "__main__":
    example_tx_hash = "0x00068206bc89986eb997dedd72653b7763618ce785987a51d7a73e907868f60d"
    
    logger.info("开始查询Gas费用...")
    gas_info = get_gas_fee_by_tx_id(example_tx_hash)
    
    if gas_info:
        print("\n=== Gas费用信息 ===")
        print(f"交易哈希: {gas_info['tx_hash']}")
        print(f"区块号: {gas_info['block_number']}")
        print(f"交易状态: {gas_info['status_text']}")
        print(f"使用的Gas: {gas_info['gas_used']:,}")
        print(f"Gas价格: {gas_info['gas_price_gwei']} Gwei")
        print(f"总Gas费用: {gas_info['total_gas_fee_eth']} ETH")
        print(f"总Gas费用: {gas_info['total_gas_fee_wei']:,} Wei")
        if 'effective_gas_price_gwei' in gas_info:
            print(f"实际Gas价格: {gas_info['effective_gas_price_gwei']} Gwei")
    else:
        print("查询失败，请检查交易哈希是否正确")

