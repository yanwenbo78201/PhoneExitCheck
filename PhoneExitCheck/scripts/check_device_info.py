#!/usr/bin/env python3
import os
import sys
import json

def find_files_with_device_info(folder_path, identifiers, generations):
    """
    遍历文件夹下的.h, .m, .swift文件，检查是否包含设备标识符或Generation信息
    
    Args:
        folder_path: 要遍历的文件夹路径
        identifiers: 设备标识符列表
        generations: Generation列表
        
    Returns:
        dict: 包含结果信息
    """
    # 需要检查的文件扩展名
    extensions = ('.h', '.m', '.swift')
    
    # 找到的文件列表
    found_files = []
    # 找到的标识符列表
    found_identifiers = set()
    # 找到的Generation列表
    found_generations = set()
    
    # 遍历文件夹
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            # 检查文件扩展名
            if file.endswith(extensions):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                        # 检查标识符
                        for identifier in identifiers:
                            if identifier in content:
                                found_files.append(file_path)
                                found_identifiers.add(identifier)
                                
                        # 检查Generation
                        for generation in generations:
                            if generation and generation in content:
                                found_files.append(file_path)
                                found_generations.add(generation)
                                
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}", file=sys.stderr)
    
    # 去重文件列表
    found_files = list(set(found_files))
    
    return {
        'folder_path': folder_path,
        'total_identifiers': len(identifiers),
        'total_generations': len([g for g in generations if g]),
        'found_identifiers': list(found_identifiers),
        'found_generations': list(found_generations),
        'found_files': found_files,
        'not_found_identifiers': [i for i in identifiers if i not in found_identifiers],
        'not_found_generations': [g for g in generations if g and g not in found_generations]
    }

def main():
    if len(sys.argv) < 4:
        print("Usage: python check_device_info.py <folder_path> <identifiers_json> <generations_json>")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    identifiers_json = sys.argv[2]
    generations_json = sys.argv[3]
    
    # 解析标识符和Generation列表
    identifiers = json.loads(identifiers_json)
    generations = json.loads(generations_json)
    
    # 检查文件夹
    result = find_files_with_device_info(folder_path, identifiers, generations)
    
    # 输出结果为JSON格式
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
