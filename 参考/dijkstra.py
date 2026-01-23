import sys
 
def dijkstra(graph, start_node):
    unvisited_nodes = {node: sys.maxsize for node in graph}  # 初始化所有节点距离为无穷大
    unvisited_nodes[start_node] = 0  # 起始节点距离为0
    shortest_paths = {start_node: (0, [])}  # 起始节点的路径和距离
 
    while unvisited_nodes:
        current_node = min(unvisited_nodes, key=unvisited_nodes.get)  # 找到未访问节点中距离最小的节点
        current_distance = unvisited_nodes[current_node]
 
        for neighbor, distance in graph[current_node].items():
            if neighbor not in unvisited_nodes: continue  # 已访问过的节点跳过
            new_distance = current_distance + distance
            if new_distance < unvisited_nodes[neighbor]:  # 如果找到更短路径，更新
                unvisited_nodes[neighbor] = new_distance
                shortest_paths[neighbor] = (new_distance, shortest_paths[current_node][1] + [current_node])  # 更新路径和距离
 
        unvisited_nodes.pop(current_node)  # 当前节点已访问过，从未访问节点中删除
 
    return shortest_paths  # 返回最短路径和距离
 
# 测试Dijkstra算法
if __name__ == "__main__":
    graph = {
        '客栈': {'e': 2, 's': 9, 'w': 9, 'n': 9},
        'B': {'A': 2, 'D': 4, 'E': 8},
        'C': {'A': 9, 'E': 10, 'F': 3},
        'D': {'B': 4, 'E': 1, 'G': 5},
        'E': {'B': 8, 'C': 10, 'D': 1, 'F': 11, 'G': 6, 'H': 12},
        'F': {'C': 3, 'E': 11, 'H': 17},
        'G': {'D': 5, 'E': 6},
        'H': {'E': 12, 'F': 17},
    }
    start_node = 'A'
    shortest_paths = dijkstra(graph, start_node)
    print(shortest_paths)