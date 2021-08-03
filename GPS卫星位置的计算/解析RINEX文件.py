"""
    您好！
    这个python文件, 是用来解析RINEX文件的，提供了解析导航电文文件(.N)和卫星观测数据文件(.O)
    里面用到的第三方库有os, sys, json,（为了函数可移植性，将import字段直接放到函数里面了）
    数据解析函数返回值为字典格式数据
    数据解析完还可导出为txt,json等文件
"""


def read_navigation_data(file_path: str):
    """读取并解析导航电文文件"""

    # 这是个内部小函数，作用是将RINEX文件格式中D19.12解析为浮点数
    def change_d19_12_to_float(src):
        # 比如:-3.733104094863D-04
        if src[0:2] == '  ':
            qian = '0'
        elif src[0:2] == ' -':
            qian = '-0'
        else:
            qian = src[0:2]
        return float(qian + '.' + src[3:-4] + 'e' + src[-3:])

    """读取RINEX格式的GPS导航电文文件，保存到一个字典返回"""
    result = {}  # 这是返回结果的字典
    all_navigation_datas = []  # 这是个列表，里面是所有卫星的导航电文数据

    # 将文件读到列表中
    with open(file_path, 'r') as f:
        all_lines = list(f.readlines())
    # print(all_lines)
    # 去掉换行符'\n'
    for i in range(len(all_lines)):
        all_lines[i] = all_lines[i].replace('\n', '')
    # 找到数据部分
    data_start_line = 0
    for i in range(len(all_lines)):
        if all_lines[i].find('END OF HEADER') != -1:
            data_start_line = i + 1
            break
    # 计算GPS导航电文数据的数量
    nums = int((len(all_lines) - data_start_line) / 8)
    if nums < 1:
        print("未找到GPS导航数据，请检查文件格式是否正确！")
        import sys
        sys.exit(-1)

    for one_nav_data in range(nums):
        nav_data_dic = {}
        nav_data_list = []
        # 先记录一下导航电文的序号,格式上补齐了前导0
        nav_data_dic['序号'] = str(one_nav_data + 1).zfill(len(str(nums)))
        """ 开始解析数据区域！"""
        # 按卫星和参考时刻存放各颗卫星的时钟和轨道数据。
        # 每颗卫星一个参考时刻的数据占8行，第0行为该卫星的PRN号、参考时刻、改正模型参数，1-7行为该卫星的广播轨道数据。
        # 由于导航电文每2h更新依次，因此一个导航电文文件包含某卫星多个不同参考时刻的数据。
        """ 明白了吗？，Let's Go! """
        # 将8行内容读到一个列表里
        for i in range(8):
            nav_data_list.append(all_lines[data_start_line + 8 * one_nav_data + i])
        # 一个导航电文一共就8行，除了第一行特殊外，其他7行都是3X,4D19.12格式，因此，用循环即可大大减少代码量
        # 第0行：PRN号，历元，卫星钟
        data_content = nav_data_list[0]
        nav_data_dic['卫星PRN号'] = int(data_content[0:2].replace(' ', '').zfill(2))  # 如果想保留前导0，就不要类型强制转换
        nav_data_dic['历元'] = data_content[2:22]
        nav_data_dic['卫星钟的偏差'] = change_d19_12_to_float(data_content[22:41])
        nav_data_dic['卫星钟漂移'] = change_d19_12_to_float(data_content[41:60])
        nav_data_dic['卫星钟漂移速度'] = change_d19_12_to_float(data_content[60:79])
        # 第1-7行：广播轨道1-7
        broadcast_tracks = [
            ['IODE', 'Crs', 'n', 'M0'],
            ['Cuc', 'e', 'Cus', 'sqrt(A)'],
            ['TOE', 'Cic', 'OMEGA', 'Cis'],
            ['i0', 'Crc', 'w', 'OMEGA_DOT'],
            ['i', 'L2_code', 'GPS_week_num', 'L2_P_code'],
            ['卫星精度', '卫星健康状态', 'TGD', 'IODC'],
            ['电文发送时刻', '拟合区间(h)', '备用1', '备用2']
        ]

        for i in range(1, 8):
            # 每隔19个字符分割
            data_content = nav_data_list[i][3:79]
            data_content = [data_content[k:k + 19] for k in range(0, len(data_content), 19)]
            for j in range(len(data_content)):
                nav_data_dic[broadcast_tracks[i - 1][j]] = change_d19_12_to_float(data_content[j])  # 用上面的广播轨道列表进行字典的创建

        all_navigation_datas.append(nav_data_dic)
    pass
    # 至此，已完成读取导航电文并存储到内存中
    # print(all_navigation_datas)
    result['导航电文文件'] = all_navigation_datas
    return result
    pass


def read_observation_data(file_path: str):
    """读取并解析观测数值文件"""
    """读取RINEX格式的观测值文件，并解析成字典返回"""
    # 将文件读到列表中
    with open(file_path, 'r') as f:
        all_lines = list(f.readlines())
    # print(all_lines)
    # 去掉换行符'\n'
    for i in range(len(all_lines)):
        all_lines[i] = all_lines[i].replace('\n', '')

    """解析观测值数据文件，保存到一个字典返回"""
    result = {}  # 这是返回结果的字典
    all_observation_datas = []  # 这是个列表，里面是所有历元的观测数据

    # 一、解析头文件
    # 1. 统计观测数据类型, 当类型大于9个时，超出部分将续行写在下n行，
    # 注意：类型数量理论上最大可为999999种，其实现实里没那么多，RINEX 2.0 定义的也就12种，不过咱不怕，有多少搞多少~~
    types_of_observ = {}
    for i in range(len(all_lines)):
        if all_lines[i].find('TYPES OF OBSERV') != -1:
            types_line_content = all_lines[i]
            data_num = int(types_line_content[:6].replace(' ', ''))
            types_of_observ['观测类型数量'] = data_num
            # 观测值列表：
            rows_of_types = data_num // 9 if data_num % 9 == 0 else data_num // 9 + 1  # 列表所占行数
            base_line_of_types = i  # 记录当前一行
            types_line_content = ''  # 先清空
            for row_num in range(rows_of_types):
                types_line_content += all_lines[base_line_of_types][6:60]
                base_line_of_types += 1
            types_line_content = types_line_content.split()  # 针对空格切片，这时types_line_content将从str变成list
            for j in range(data_num):
                types_of_observ['观测类型' + str(j + 1)] = types_line_content[j]
            # 头文件其他信息不用遍历，统计完数据类型就可以退出了
            break
    pass
    # 二、解析数据区域，即观测数据
    datas_of_observ = {}
    # 1. 定位数据区域
    data_start_line = 0
    for i in range(len(all_lines)):
        if all_lines[i].find('END OF HEADER') != -1:
            data_start_line = i + 1
            break
    if int(len(all_lines) - data_start_line) < 1:
        print("未找到观测值数据，请检查文件格式是否正确！")
        import sys
        sys.exit(-1)
    # 2. 解析数据区域
    """ 开始解析数据区域！"""
    # 按历元依次存放观测数据或观测过程中发生的事件信息
    # 每个历元的数据包含两部分：
    # 1. 第一部分：每个历元/卫星或事件标志，通常为第一行，
    # 注意：当卫星数量超过12，或有事件发生时，会有紧跟着的多行。卫星数量理论上最大可为999个，不过现实里没那么多，最多也就十几个
    # 2. 第二部分：观测值，存放该历元所有卫星所采集到的所有观测值，所占行数与卫星数量、观测值类型数量有关。
    # 注意：当观测值类型数量超过5种时，超出部分将续行写在下一行，这是因为一行只能放5个数据(80/16)。
    # 3. 备注：历元之间的时间间隔在头文件中INTERVAL部分指出，通常为若干秒，例如10s，30s
    """ 明白了吗？，Let's Go! """

    Epoch_serial_number: int = 0  # 每个历元的序号
    Epoch_serial_row: int = data_start_line  # 每个历元开始的行号
    while Epoch_serial_row < len(all_lines):
        # o_dic = {}
        """每次进入这个循环，都是一个新的历元"""
        # 1. 第一部分：每个历元，事件标志，卫星数量及列表
        one_Epoch_dic = {}  # 记录一个历元数据
        part_one = all_lines[Epoch_serial_row]  # 这是第一部分的一行字符串
        Epoch_serial_number += 1
        one_Epoch_dic['历元序号'] = Epoch_serial_number
        one_Epoch_dic['观测历元时刻'] = part_one[1:26]
        one_Epoch_dic['历元标志'] = int(part_one[28:29])
        satellite_num = int(part_one[29:32].strip(' '))  # 卫星数量
        one_Epoch_dic['卫星数量'] = satellite_num
        satellites_observ_data = []  # 记录所有卫星的所有数据
        # 卫星列表：
        # 当数量大于12时，超出部分将续行写在下n行，
        # 注意：卫星数量理论上最大可为999个，其实现实里没那么多，最多也就十几个，不过咱不怕，继续有多少搞多少~~
        rows_of_satellites = satellite_num // 12 if satellite_num % 12 == 0 else satellite_num // 12 + 1
        base_line_of_sat = Epoch_serial_row  # 记录当前一行
        part_one = ''  # 先清空
        for row_num in range(rows_of_satellites):
            part_one += all_lines[base_line_of_sat][32:68]
            base_line_of_sat += 1
        part_one = [part_one[i:i + 3] for i in range(0, len(part_one), 3)]  # 每隔三个字符串切片，这个方法很实用，请尽量掌握~~
        for j in range(satellite_num):
            one_satellite_dic = {'卫星{}的PRN号'.format(str(j + 1)): part_one[j]}  # 一个卫星一个新的字典
            satellites_observ_data.append(one_satellite_dic)
        pass

        # 2. 第二部分：观测值，存放该历元所有卫星所采集到的所有观测值，所占行数与卫星数量、观测值类型数量有关。
        # 注意：当观测值类型数量超过5种时，超出部分将续行写在下一行，这是因为一行只能放5个数据(80/16)。不过咱还是不怕，干就完了！
        # 2.1 通过观测类型数量，计算每个卫星的观测数据占几行
        rows_of_each_satellite_data = types_of_observ['观测类型数量'] // 5 if types_of_observ['观测类型数量'] % 5 == 0 else \
            types_of_observ['观测类型数量'] // 5 + 1
        # 2.2 遍历该历元下所有卫星，读取所有卫星的观测值
        base_line_of_data_type = base_line_of_sat  # 记录当前一行
        for sn in range(satellite_num):
            # sn_PRN = satellites_observ_data[sn]['卫星PRN号']  # 当前正在处理的卫星的PRN号
            # print('当前读取数据的卫星号', sn_PRN)
            """再次使用上面那个厉害的算法（核心：循环+切片），循环读取该卫星所有观测类型的数据~~"""
            part_two = ''
            for row_num in range(rows_of_each_satellite_data):
                temp = all_lines[base_line_of_data_type][0:80]
                if row_num < rows_of_each_satellite_data - 1:
                    if len(temp) == 0:
                        for jj in range(5):
                            part_two += '                '
                    if len(temp) % 16 == 14:
                        part_two += temp + '  '
                    elif len(temp) % 16 == 15:
                        part_two += temp + ' '
                    else:
                        part_two += temp
                else:
                    if len(temp) < 16*(types_of_observ['观测类型数量'] - row_num * 5) -2:
                        if len(temp) % 16 == 14:
                            temp += temp + '  '
                        elif len(temp) % 16 == 15:
                            temp += temp + ' '
                        part_two += temp
                        for jj in range(int(types_of_observ['观测类型数量']) - row_num * 5-len(temp)//16):
                            part_two += '                '
                    else:
                        if len(temp) % 16 == 14:
                            part_two += temp + '  '
                        elif len(temp) % 16 == 15:
                            part_two += temp + ' '
                        else:
                            part_two += temp
                base_line_of_data_type += 1
            dd = part_two
            part_two = [part_two[i:i + 16] for i in range(0, len(part_two), 16)]  # 每隔16个字符串切片，每一个对应一个观测数据(F14.3,I1,I1)
            # 读取完毕，那就用一个循环把数据记到字典里吧！(字典里添加新元素)
            for each_type_num in range(0, types_of_observ['观测类型数量']):
                try:
                    one_record = {
                        '观测值': '空' if part_two[each_type_num][0:14] == '              ' else float(
                            part_two[each_type_num][0:14].strip()),
                        'LLI失锁标识符': '空' if part_two[each_type_num][14] == ' ' else int(
                            part_two[each_type_num][14]),
                        '信号强度': '空' if part_two[each_type_num][15] == ' ' else int(
                            part_two[each_type_num][15])
                    }
                    satellites_observ_data[sn][types_of_observ['观测类型' + str(each_type_num + 1)]] = one_record
                    # print(types_of_observ['观测类型' + str(each_type_num + 1)], ' 未处理的观测值: ', part_two[each_type_num])  # 测试用
                except Exception as e:
                    print('源文件格式错误？请检查文件{}的第{}行附近有没有格式错误！具体错误代码：{}'.format(file_name, base_line_of_data_type-1, e))
            # 一个卫星结束
        pass
        # 至此，一个历元下所有卫星的数据读取完毕，保存一下，就进入下一个历元接着读~~
        one_Epoch_dic['所有卫星数据'] = satellites_observ_data
        all_observation_datas.append(one_Epoch_dic)
        Epoch_serial_row = base_line_of_data_type
    pass
    # 至此，已完成读取卫星观测数据并存储到内存中
    # print(all_observation_datas)
    result['卫星观测数据文件'] = all_observation_datas
    return result
    pass


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
    # 解析RINEX格式的导航电文和卫星观测数据到内存中（字典类型），并导出到txt或json格式文件
    # 打招呼
    print("Hello, 这个程序的作用是：\n解析RINEX格式的导航电文和卫星观测数据到内存中（字典类型），并导出到txt或json格式文件")
    print("\n-------------------------- 这是一个分割线 --------------------------------\n")

    # 解析导航电文文件
    file_name = input("输入要解析的导航电文文件地址和名字：(例如：./原始数据/00052731.98N)\n")
    nav_data = read_navigation_data(file_name)

    # 打印数据
    print("解析完毕，是否需要打印到控制台(1：是  2： 否)")
    is_print = input("请输入您的选择：")
    if is_print == "1":
        print(nav_data)

    # 导出数据
    print("是否需要保存到文件(1：是  2： 否)")
    is_write = input("请输入您的选择：")
    if is_write == "1":
        path = input("保存地址：(例如：./解析结果/)\n")
        name = file_name.split('/')[-1]
        write_dict_to_file(nav_data, path, name + '.txt')
        write_dict_to_file(nav_data, path, name + '.json')
        print("保存完毕，结果已保存到：", path)

    print("\n-------------------------- 这是一个分割线 --------------------------------\n")
    # 解析卫星观测数据文件，用户交互菜单同上
    file_name = input("输入要解析的卫星观测数据文件地址和名字：(例如：./原始数据/00052731.98O)\n")
    obs_data = read_observation_data(file_name)

    # 打印数据
    print("解析完毕，是否需要打印到控制台(1：是  2： 否)")
    is_print2 = input("请输入您的选择：")
    if is_print2 == "1":
        print(obs_data)

    # 导出数据
    print("是否需要保存到文件(1：是  2： 否)")
    is_write2 = input("请输入您的选择：")
    if is_write2 == "1":
        path = input("保存地址：(例如：./解析结果/)\n")
        name = file_name.split('/')[-1]
        write_dict_to_file(obs_data, path, name + '.txt')
        write_dict_to_file(obs_data, path, name + '.json')
        print("保存完毕，结果已保存到：", path)

    print("\n-------------------------- 这是一个分割线 --------------------------------\n")
    # 结束语
    print("很高兴为您服务，下次再见~~")
