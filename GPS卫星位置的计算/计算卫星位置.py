#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# @Author: PAYIZ
# @project: GPS卫星位置的计算
# @File : 计算卫星位置.py
# @Time : 2020/12/20 21:30
# 需要安装第三方库？试试这个语句(使用清华镜像源)：pip --default-timeout=100 install -i https://pypi.tuna.tsinghua.edu.cn/simple name
# -----------------------------------

"""
    您好！
    这个python文件, 是用来解析RINEX格式的导航电文到内存中（字典类型），
    计算其中所有卫星在瞬时地球坐标系(WGS-84)中的位置，并导出到txt或json格式文件
    里面用到的第三方库有os, sys, json,pandas,math（为了函数可移植性，将有些import字段直接放到函数里面了）
    数据解析函数返回值为字典格式数据
    数据解析完还可导出为txt,json等文件
    注意：本文件还用到了我自己写的 解析RINEX文件.py 文件中的函数： read_navigation_data
    若无该文件请联系本人获取，谢谢！
"""


import math

from 解析RINEX文件 import read_navigation_data


def calculation_of_gps_satellite_position(file_path):
    """读取导航电文并解析，这一部分调用了 ”解析RINEX文件.py“ 代码文件里面的函数"""
    nav_file = read_navigation_data(file_path)
    nav_data = nav_file['导航电文文件']
    # 定义一些常量
    e_E = 1 / 298.257223563  # 地球扁率：
    OMEGA_E = 7.292115 * 10 ** (-5)  # 地球自转角速度：rad/s
    GM = 3.9860044 * 10 ** 14  # 地心引力常数： m3/s2
    c = 299792458  # 真空中的光速：m/s

    """
    # 这里是导航电文解析完保存成字典里面的广播轨道信息,为了写代码、读代码方面就以注释的方式放在此处
    broadcast_tracks = [
        ['IODE', 'Crs', 'n', 'M0'],
        ['Cuc', 'e', 'Cus', 'sqrt(A)'],
        ['TOE', 'Cic', 'OMEGA', 'Cis'],
        ['i0', 'Crc', 'w', 'OMEGA_DOT'],
        ['i', 'L2_code', 'GPS_week_num', 'L2_P_code'],
        ['卫星精度', '卫星健康状态', 'TGD', 'IODC'],
        ['电文发送时刻', '拟合区间(h)', '备用1', '备用2']
    ]
    """
    # 循环计算观测到的卫星的位置，结果依然保存到一个字典里
    result = {}  # 这是返回结果的字典
    all_satellites_positions = []  # 这是个列表，里面是所有卫星的位置数据

    for one_satellite in nav_data:
        # print(one_satellite)

        # 1. 计算卫星运动的平均角速度n
        square_A = one_satellite['sqrt(A)']
        n0 = math.sqrt(GM) / (square_A ** 3)
        n = n0 + one_satellite['n']

        # 2. 计算观测瞬间卫星的平近点角M
        # 2.1 计算离该历元的前周日零点的时间差t，即周内秒数
        Epoch_list = [one_satellite['历元'][i:i + 3] for i in range(0, len(one_satellite['历元']), 3)]
        Epoch = {
            'year': int('19' + Epoch_list[0].strip()) if 80 <= int(Epoch_list[0]) <= 99 else int(
                '20' + Epoch_list[0].strip()),
            'month': int(Epoch_list[1]),
            'day': int(Epoch_list[2]),
            'hour': int(Epoch_list[3]),
            'min': int(Epoch_list[4]),
            'sec': float(Epoch_list[5] + Epoch_list[6])
        }
        # 2.1.1 计算该历元是星期几
        import datetime
        which_one = datetime.date(Epoch["year"], Epoch['month'], Epoch['day']).weekday()
        # week_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        # date_name = week_days[which_one]   # 测试用

        # 2.1.2 计算周内秒数t
        t = ((which_one + 1) * 24 + Epoch['hour']) * 3600 + Epoch['min'] * 60 + Epoch['sec']

        # 2.2 通过公式计算卫星的平近点角M
        TOE = one_satellite['TOE']
        M = one_satellite['M0'] + n * (t - TOE)

        # 3. 计算偏近点角 E
        e = one_satellite['e']

        # 用弧度表示的开普勒方程
        # E = M + e * math.sin(M)
        # 迭代法计算上述方程
        E: float = 0
        Ek = M
        while True:
            Ek1 = Ek + e * math.sin(Ek)
            if math.fabs(Ek1 - Ek) <= 1e-12:
                E = Ek1  # 将结果存到E,退出循环
                break
            else:
                # print('现在二者相差：', math.fabs(Ek1 - Ek))  # 测试用
                Ek = Ek1  # 继续迭代
                continue
            pass

        # 4. 计算真近点角f
        f = math.atan2(math.sqrt(1 - e * e) * math.sin(E), (math.cos(E) - e))

        # 5. 计算升交距角u', 在这里命名为u_pie
        u_pie = one_satellite['w'] + f

        # 6. 计算摄动改正项δ_u、δ_r、δ_i , 这里命名时前缀用delta表示
        delta_u = one_satellite['Cuc'] * math.cos(2 * u_pie) + one_satellite['Cus'] * math.sin(2 * u_pie)
        delta_r = one_satellite['Crc'] * math.cos(2 * u_pie) + one_satellite['Crs'] * math.sin(2 * u_pie)
        delta_i = one_satellite['Cic'] * math.cos(2 * u_pie) + one_satellite['Cis'] * math.sin(2 * u_pie)

        # 7. 对u'、r'、i0进行摄动改正
        u = u_pie + delta_u
        r = square_A ** 2 * (1 - e * math.cos(E)) + delta_r
        i = one_satellite['i0'] + delta_i + one_satellite['i'] * (t - TOE)

        # 8. 计算卫星在轨道面坐标系中的位置
        x = r * math.cos(u)
        y = r * math.sin(u)
        z = 0

        # 9.计算观测瞬间升交点的精度L
        L = one_satellite['OMEGA'] + one_satellite['OMEGA_DOT'] * (t - TOE) - OMEGA_E * t

        # 10. 计算卫星在瞬时地球坐标系(WGS-84)中的位置
        coordinate_wgs_84 = {
            'X': x * math.cos(L) - y * math.cos(i) * math.sin(L),
            'Y': x * math.sin(L) - y * math.cos(i) * math.cos(L),
            'Z': y * math.sin(i)
        }

        # 11. 计算卫星在协议地球坐标系中的位置(考虑极移的影响),得出coordinate_cts:conventional terrestrial system
        # 极移参数采用了国际地球自转和参考系统服务（网址：http://www.iers.org）提供的美国海军天文台和法国巴黎天文台的地极移动预测结果
        # 找到2020年12月发表的标准参数，并只取了2020全年的平均值 0.049,0.032
        # 需要更精确的话请自行改成目标年份目标日期的地极参数（我不想实现了，因为没有找到往年的参数）
        # 如需更精确的方法，请参考ITRS和ITRF

        # polar coordinates xp, yp
        xp = 0.049
        yp = 0.032

        coordinate_cts = {
            'X': coordinate_wgs_84['X'] + coordinate_wgs_84['Z'] * xp,
            'Y': coordinate_wgs_84['Y'] - coordinate_wgs_84['Z'] * yp,
            'Z': (-1) * coordinate_wgs_84['X'] * xp + coordinate_wgs_84['Y'] * yp + coordinate_wgs_84['Z']
        }
        # print('当前被计算的卫星：', one_satellite['卫星PRN号'], one_satellite['历元'])
        # print('计算卫星在瞬时地球坐标系(WGS-84)中的位置：', coordinate_wgs_84)
        # print('卫星在协议地球坐标系中的位置：', coordinate_cts, '\n')

        # 返回结果
        # 因为老师只要求瞬时地球坐标系(WGS-84)中的位置，因此就只返回这个
        # 因为导航电文每隔2h发一次，因此每颗卫星会有多个位置信息
        one_satellite_positions = {
            '卫星PRN号': one_satellite['卫星PRN号'],
            '所有位置': [
                {
                    '历元': one_satellite['历元'],
                    'WGS-84坐标系位置': coordinate_wgs_84
                }
            ]
        }

        # 状态标志
        flag = 0  # 0： 默认无该卫星
        for i in all_satellites_positions:
            if i['卫星PRN号'] == one_satellite_positions['卫星PRN号']:
                flag = 1
                for j in i['所有位置']:
                    if j['历元'] == one_satellite_positions['所有位置'][0]['历元']:
                        # 存在该卫星及该历元时位置，处理方式：跳过
                        flag = 2
                        break
                if flag == 1:
                    # 存在该卫星但没有该历元时位置，处理方式：添加新的位置
                    i['所有位置'].append(one_satellite_positions['所有位置'][0])
                    break
        pass
        if flag == 0:
            # 没找到该卫星的位置记录，处理方式：添加该卫星的记录
            all_satellites_positions.append(one_satellite_positions)

        # break  # 这个停顿是测试时用的
    # 至此，已完成读取卫星位置的计算并存储到内存中
    result['所有卫星在瞬时地球坐标系(WGS-84)中的位置'] = all_satellites_positions
    return result


def write_dict_to_file(dict_data, file_path, file_name):
    """将读到内存中的字典类型数据保存到各种文件中"""
    # 目前只写了txt和json两种格式
    import os
    if not os.path.exists(file_path):
        os.makedirs(file_path)
    output_type = file_name.split('.')[-1]
    if output_type == 'txt':
        # txt文件
        with open(file_path + file_name, 'w', encoding='utf-8') as f_c:
            f_c.write(str(dict_data))
    else:
        # json文件
        import json
        with open(file_path + file_name.replace(file_name.split('.')[-1], '') + 'json', 'w', encoding='utf-8') as f:
            json.dump(dict_data, f, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    # 解析RINEX格式的导航电文到内存中（字典类型），计算其中所有卫星在瞬时地球坐标系(WGS-84)中的位置，并导出到txt或json格式文件
    # 打招呼
    print("Hello, 这个程序的作用是：\n解析RINEX格式的导航电文到内存中（字典类型），计算其中所有卫星在瞬时地球坐标系(WGS-84)中的位置，并导出到txt或json格式文件")
    print("\n-------------------------- 这是一个分割线 --------------------------------\n")

    # 解析导航电文文件
    file_name = input("输入要解析的导航电文文件地址和名字：(例如：./原始数据/00052731.98N)\n")
    positions = calculation_of_gps_satellite_position(file_name)

    # 打印数据
    print("解析完毕，是否需要打印到控制台(1：是  2： 否)")
    is_print = input("请输入您的选择：")
    if is_print == "1":
        print(positions)

    # 导出数据
    print("是否需要保存到文件(1：是  2： 否)")
    is_write = input("请输入您的选择：")
    if is_write == "1":
        path = input("保存地址：(例如：./卫星位置计算结果/)\n")
        name = file_name.split('/')[-1]
        write_dict_to_file(positions, path, name + '.txt')
        write_dict_to_file(positions, path, name + '.json')
        print("保存完毕，结果已保存到：", path)

    print("\n-------------------------- 这是一个分割线 --------------------------------\n")
    # 结束语
    print("很高兴为您服务，下次再见~~")
