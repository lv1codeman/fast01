import requests

url = "http://localhost:8000/query/"  # 替换为你的服务器地址

query_params = {
    "year": "112",
    "semester": "2",
    "crsnm": "計算機",
    # 可以根据需要添加其他查询参数
}

response = requests.post(url, json=query_params)

if response.status_code == 200:
    data = response.json()
    courses = data["courses"]
    for course in courses:
        print(course)
else:
    print("Failed to query courses. Status code:", response.status_code)
