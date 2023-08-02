import os, pandas as pd, sys
sys.path.insert(0, 'C:/EnergyPlusV22-1-0')

from pyenergyplus.api import EnergyPlusAPI
ep_api = EnergyPlusAPI()
state = ep_api.state_manager.new_state()
psychrometric = ep_api.functional.psychrometrics(state)


def date_time_to_epw_ith_row_in_normal_year(date_time):
    # 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31
    hours_in_normal_year = [744, 672, 744, 720, 744, 720, 744, 744, 720, 744, 720, 744]
    month = date_time.month
    day = date_time.day
    hour = date_time.hour
    ith_hour = sum(hours_in_normal_year[:month - 1]) + (day - 1) * 24 + hour
    # ith_hour to ith_row
    ith_row = ith_hour + 8
    return ith_row

def generate_epw():
    
    epw_Template_file_path = os.path.join('./resources/epw', 
        'USA_IL_Chicago-OHare.Intl.AP.725300_TMY3_No_Precipitable_Water.epw')
    
    vcwg_prediction_saving_path = os.path.join('A_saved_Cases',
        'one-way-Scalar_ShoeBox_MedOffice',
        'VCWG_EP_Online_Scalar_ShoeBox_MedOffice.csv')
    generated_epw_path = os.path.join('A_saved_Cases',
        'one-way-Scalar_ShoeBox_MedOffice',
        'One-Way-Scalar_ShoeBox_MedOffice.epw')
    vcwg_outputs = pd.read_csv(vcwg_prediction_saving_path, index_col=0, parse_dates=True)
    vcwg_outputs_hourly = vcwg_outputs.resample('H').mean()
    '''
    VCWG hour is 0-23, while epw hour is 1-24
    '''
    # read text based epw file line by line
    with open(epw_Template_file_path, 'r') as f:
        lines = f.readlines()
        # iterate through vcwg_outpouts_hourly.index
        for i, date_time in enumerate(vcwg_outputs_hourly.index):
            ith_row = date_time_to_epw_ith_row_in_normal_year(date_time)
            lines[ith_row] = lines[ith_row].split(',')
            vcwg_prediction = vcwg_outputs_hourly.iloc[i]
            dry_bulb_c = vcwg_prediction['canTemp_K'] - 273.15
            vcwg_canSpecHum_Ratio = vcwg_prediction['hum_ratio']
            press_pa = vcwg_prediction['vcwg_canPress_pa']
            relative_humidity_percentage = 100*psychrometric.relative_humidity_b(state, dry_bulb_c,
                                               vcwg_canSpecHum_Ratio, press_pa)
            dew_point_c = psychrometric.dew_point(state, vcwg_canSpecHum_Ratio, press_pa)
            lines[ith_row][6] = str(dry_bulb_c)
            lines[ith_row][7] = str(dew_point_c)
            lines[ith_row][8] = str(relative_humidity_percentage)
            lines[ith_row][9] = str(press_pa)
            lines[ith_row] = ','.join(lines[ith_row])
    with open(generated_epw_path, 'w') as f:
        f.writelines(lines)

if __name__ == '__main__':
    generate_epw()