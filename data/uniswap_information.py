import json

import requests
import yaml

from loguru import logger

with open("config/config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

API_KEY = config["the_graph"]["api_key"]
GRAPH_API_URL = config["the_graph"]["graph_api_url"]
POOL_ADDRESS = config["the_graph"]["uniswap_pool_address"]

# GraphQL 查询语句
# 查询 pool 实体，通过 id (即合约地址) 过滤
query = """
query PoolFeeQuery {
  pool(id: "0x%lx") {
    id
    token0 {
      symbol
      name
    }
    token1 {
      symbol
      name
    }
    feeTier
    totalValueLockedUSD
  }
}
"""% (POOL_ADDRESS)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
payload = {'query': query}

logger.info(f"正在查询 Pool 地址: {POOL_ADDRESS}")

try:
    # 发送 POST 请求
    response = requests.post(GRAPH_API_URL, headers=headers, data=json.dumps(payload))
    response.raise_for_status() # 检查 HTTP 错误

    data = response.json()

    # 检查 GraphQL 返回的错误
    if 'errors' in data:
        logger.error("GraphQL 查询返回错误:")
        print(json.dumps(data['errors'], indent=2))
        logger.error(f"GraphQL 查询返回错误: {data['errors']}")

    pool_info = data.get('data', {}).get('pool')

    if pool_info:
        # 提取费率信息
        fee_tier = int(pool_info['feeTier'])
        fee_percent = fee_tier / 10000
        print("===Uniswap Pool Information===")
        print(f"Pool 地址: {pool_info['id']}")
        print(f"交易对: {pool_info['token0']['symbol']}/{pool_info['token1']['symbol']}")
        print(f"代币名称: {pool_info['token0']['name']} / {pool_info['token1']['name']}")
        print(f"交易费率: {fee_percent:.2f}%")
        print(f"TVL (USD): ${float(pool_info['totalValueLockedUSD']):,.2f}")
    else:
        logger.error(f"在 Uniswap V3 Subgraph 中找不到地址为 {POOL_ADDRESS} 的 Pool 信息。")
except requests.exceptions.RequestException as e:
    logger.error(f"HTTP 请求发生错误: {e}")
except Exception as e:
    logger.error(f"处理数据时发生未知错误: {e}")