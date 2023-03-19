from threading import Thread
import _1_parent_coordination as coordination
from VCWG_Hydrology import VCWG_Hydro
import os, signal

def run_vcwg():
    if 'None' in coordination.TopForcingFileName:
        TopForcingFileName = None
        epwFileName = coordination.epwFileName
    else:
        epwFileName = None
        TopForcingFileName = coordination.TopForcingFileName
    VCWGParamFileName = coordination.VCWGParamFileName
    ViewFactorFileName = f'{coordination.bld_type}_ViewFactor.txt'
    # Case name to append output file names with
    case = f'{coordination.bld_type}'
    # Initialize the UWG object and run the simulation
    VCWG = VCWG_Hydro(epwFileName, TopForcingFileName, VCWGParamFileName, ViewFactorFileName, case)
    VCWG.run()
def _get_midRiseApart_roof_actuator_handle(state):
    _surfaces = ['t Roof SWA', 't Roof NWA', 't Roof SEA', 't Roof NEA',
                 't Roof N1A', 't Roof N2A','t Roof S1A', 't Roof S2A', 't Roof C']
    _actuator_handles = []
    for _surface in _surfaces:
        _actuator_handle = coordination.ep_api.exchange. \
            get_actuator_handle(state, "Surface", "Exterior Surface Convection Heat Transfer Coefficient", \
                                _surface)
        if _actuator_handle < 0:
            print(f'get_midRiseApart_roof_actuator_handle(): actuator handle not available for {_surface}')
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)
        _actuator_handles.append(_actuator_handle)
    return _actuator_handles
def overwrite_ep_weather(state):
    global odb_actuator_handle, orh_actuator_handle,roof_hConv_act_lst, \
        wsped_mps_actuator_handle, wdir_deg_actuator_handle,zone_flr_area_handle

    if not coordination.overwrite_ep_weather_inited_handle:
        if not coordination.ep_api.exchange.api_data_fully_ready(state):
            return
        coordination.overwrite_ep_weather_inited_handle = True
        odb_actuator_handle = coordination.ep_api.exchange.\
            get_actuator_handle(state, "Weather Data", "Outdoor Dry Bulb", "Environment")
        orh_actuator_handle = coordination.ep_api.exchange.\
            get_actuator_handle(state, "Weather Data", "Outdoor Relative Humidity", "Environment")

        if 'Detailed_MedOffice' in coordination.bld_type:
            roof_hConv_actuator_handle = coordination.ep_api.exchange. \
                get_actuator_handle(state, "Surface", "Exterior Surface Convection Heat Transfer Coefficient", \
                                    "BUILDING_ROOF")
            if roof_hConv_actuator_handle < 0:
                print('get medium office roof actuator handle failed')
                os.getpid()
                os.kill(os.getpid(), signal.SIGTERM)
            roof_hConv_act_lst = [roof_hConv_actuator_handle]
        elif 'MidRiseApartment' in coordination.bld_type:
            roof_hConv_act_lst = _get_midRiseApart_roof_actuator_handle(state)
        if odb_actuator_handle * orh_actuator_handle< 0:
            print('ovewrite_ep_weather():some handle not available')
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)

    warm_up = coordination.ep_api.exchange.warmup_flag(state)
    if not warm_up:
        if not coordination.called_vcwg_bool:
            coordination.called_vcwg_bool = True
            Thread(target=run_vcwg).start()
        coordination.sem1.acquire()
        rh = 100*coordination.psychrometric.relative_humidity_b(state, coordination.vcwg_canTemp_K - 273.15,
                                               coordination.vcwg_canSpecHum_Ratio, coordination.vcwg_canPress_Pa)
        coordination.ep_api.exchange.set_actuator_value(state, odb_actuator_handle, coordination.vcwg_canTemp_K - 273.15)
        coordination.ep_api.exchange.set_actuator_value(state, orh_actuator_handle, rh)
        for roof_hConv_actuator_handle in roof_hConv_act_lst:
            coordination.ep_api.exchange.set_actuator_value(state, roof_hConv_actuator_handle, coordination.vcwg_hConv_w_m2_per_K)
        coordination.sem2.release()#

def _medium_get_sensor_handles(state):
    handles_dict = {}
    hvac_heat_rejection_sensor_handle = \
        coordination.ep_api.exchange.get_variable_handle(state, \
                                                         "HVAC System Total Heat Rejection Energy", \
                                                         "SIMHVAC")
    roof_Text_handle = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature", \
                                                                        "Building_Roof")
    if hvac_heat_rejection_sensor_handle * roof_Text_handle < 0:
        print("MediumOffice_get_handles: hvac_heat_rejection_sensor_handle * roof_Text_handle < 0")
        os.getpid()
        os.kill(os.getpid(), signal.SIGTERM)
    handles_dict['simhvac'] = hvac_heat_rejection_sensor_handle
    handles_dict['roof_Text'] = [roof_Text_handle]
    handles_dict['floor_Text'] = []
    flr_surfaces = ['Perimeter_bot_ZN_1_Floor', 'Perimeter_bot_ZN_2_Floor', 'Perimeter_bot_ZN_3_Floor',
                    'Perimeter_bot_ZN_4_Floor', 'Core_bot_ZN_5_Floor']
    for surface in flr_surfaces:
        _tmp = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature", \
                                                                                 surface)
        if _tmp < 0:
            print("MediumOffice_get_handles: _tmp < 0")
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)
        handles_dict['floor_Text'].append(_tmp)

    handles_dict['s_wall_Text'] = []
    handles_dict['s_wall_Solar'] = []
    handles_dict['n_wall_Text'] = []
    handles_dict['n_wall_Solar'] = []
    _levels = ['bot', 'mid', 'top']
    for level in _levels:
        _tmp_SText = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature", \
                                                                        "Perimeter_" + level + "_ZN_1_Wall_South")
        _tmp_SSolar = coordination.ep_api.exchange.get_variable_handle(state, \
                                                                        "Surface Outside Face Incident Solar Radiation Rate per Area", \
                                                                        "Perimeter_" + level + "_ZN_1_Wall_South")
        _tmp_NText = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature", \
                                                                        "Perimeter_" + level + "_ZN_3_Wall_North")
        _tmp_NSolar = coordination.ep_api.exchange.get_variable_handle(state, \
                                                                        "Surface Outside Face Incident Solar Radiation Rate per Area", \
                                                                        "Perimeter_" + level + "_ZN_3_Wall_North")
        if _tmp_SText * _tmp_SSolar * _tmp_NText * _tmp_NSolar < 0:
            print("MediumOffice_get_handles: _tmp_SText * _tmp_SSolar * _tmp_NText * _tmp_NSolar < 0")
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)
        handles_dict['s_wall_Text'].append(_tmp_SText)
        handles_dict['s_wall_Solar'].append(_tmp_SSolar)
        handles_dict['n_wall_Text'].append(_tmp_NText)
        handles_dict['n_wall_Solar'].append(_tmp_NSolar)
    return handles_dict

def _get_sensor_values(state, handleDict):
    _roof_Text_c = 0
    _floor_Text_c = 0
    _s_wall_Text_c = 0
    _s_wall_Solar_w_m2 = 0
    _n_wall_Text_c = 0
    _n_wall_Solar_w_m2 = 0

    for i in range(len(handleDict['roof_Text'])):
        _roof_Text_c += coordination.ep_api.exchange.get_variable_value(state, handleDict['roof_Text'][i])
    for i in range(len(handleDict['floor_Text'])):
        _floor_Text_c += coordination.ep_api.exchange.get_variable_value(state, handleDict['floor_Text'][i])

    for i in range(len(handleDict['s_wall_Text'])):
        _s_wall_Text_c += coordination.ep_api.exchange.get_variable_value(state, handleDict['s_wall_Text'][i])
        _n_wall_Text_c += coordination.ep_api.exchange.get_variable_value(state, handleDict['n_wall_Text'][i])
    _roof_Text_c /= len(handleDict['roof_Text'])
    _floor_Text_c /= len(handleDict['floor_Text'])
    _s_wall_Text_c /= len(handleDict['s_wall_Text'])
    _n_wall_Text_c /= len(handleDict['n_wall_Text'])
    return _roof_Text_c, _floor_Text_c, _s_wall_Text_c, _n_wall_Text_c

def _midRiseApar_get_sensor_handles(state):
    handles_dict = {}
    hvac_heat_rejection_sensor_handle = \
        coordination.ep_api.exchange.get_variable_handle(state, \
                                                         "HVAC System Total Heat Rejection Energy", \
                                                         "SIMHVAC")
    if hvac_heat_rejection_sensor_handle < 0:
        print("MediumOffice_get_handles: hvac_heat_rejection_sensor_handle < 0")
        os.getpid()
        os.kill(os.getpid(), signal.SIGTERM)
    handles_dict['simhvac'] = hvac_heat_rejection_sensor_handle

    handles_dict['roof_Text'] = []
    handles_dict['floor_Text'] = []
    handles_dict['s_wall_Text'] = []
    handles_dict['n_wall_Text'] = []

    _roofSurfaces = ['t Roof SWA', 't Roof SEA', 't Roof S1A', 't Roof S2A',
                     't Roof NWA', 't Roof NEA', 't Roof N1A', 't Roof N2A',
                     't Roof C']
    _floorSurfaces = ['g GFloor SWA', 'g GFloor SEA', 'g GFloor S1A', 'g GFloor S2A',
                      'g GFloor NWA', 'g GFloor NEA', 'g GFloor N1A', 'g GFloor N2A']
    _sWallSurfaces = ['g SWall SWA', 'g SWall SEA', 'g SWall S1A', 'g SWall S2A',
                      'm SWall SWA', 'm SWall SEA', 'm SWall S1A', 'm SWall S2A',
                      't SWall SWA', 't SWall SEA', 't SWall S1A', 't SWall S2A']
    _nWallSurfaces = ['g NWall NWA', 'g NWall NEA', 'g NWall N1A', 'g NWall N2A',
                        'm NWall NWA', 'm NWall NEA', 'm NWall N1A', 'm NWall N2A',
                        't NWall NWA', 't NWall NEA', 't NWall N1A', 't NWall N2A']
    for surface in _roofSurfaces:
        handles_dict['roof_Text'].append(coordination.ep_api.exchange.get_variable_handle(state, \
                                                                                       "Surface Outside Face Temperature", \
                                                                                       surface))
    for surface in _floorSurfaces:
        handles_dict['floor_Text'].append(coordination.ep_api.exchange.get_variable_handle(state, \
                                                                                        "Surface Outside Face Temperature", \
                                                                                        surface))
    for surface in _sWallSurfaces:
        handles_dict['s_wall_Text'].append(coordination.ep_api.exchange.get_variable_handle(state, \
                                                                                         "Surface Outside Face Temperature", \
                                                                                         surface))
    for surface in _nWallSurfaces:
        handles_dict['n_wall_Text'].append(coordination.ep_api.exchange.get_variable_handle(state, \
                                                                                         "Surface Outside Face Temperature", \
                                                                                         surface))
    for _k, _vlist in handles_dict.items():
        if _k == 'simhvac':
            continue
        for _v in _vlist:
            if _v < 0:
                print("MediumOffice_get_handles: {} < 0".format(_k))
                os.getpid()
                os.kill(os.getpid(), signal.SIGTERM)
    return handles_dict
def medOff_midApart_get_ep_results(state):
    global hanldesDict

    if not coordination.get_ep_results_inited_handle:
        if not coordination.ep_api.exchange.api_data_fully_ready(state):
            return
        coordination.get_ep_results_inited_handle = True
        if 'Detailed_MedOffice' in coordination.bld_type:
            hanldesDict = _medium_get_sensor_handles(state)
        elif 'Detailed_MidRiseApartment' in coordination.bld_type:
            hanldesDict = _midRiseApar_get_sensor_handles(state)

    if coordination.called_vcwg_bool:

        coordination.sem2.acquire()
        curr_sim_time_in_hours = coordination.ep_api.exchange.current_sim_time(state)
        curr_sim_time_in_seconds = curr_sim_time_in_hours * 3600  # Should always accumulate, since system time always advances
        accumulated_time_in_seconds = curr_sim_time_in_seconds - coordination.ep_last_call_time_seconds
        coordination.ep_last_call_time_seconds = curr_sim_time_in_seconds
        hvac_heat_rejection_J = coordination.ep_api.exchange.get_variable_value(state,hanldesDict['simhvac'])
        hvac_waste_w_m2 = hvac_heat_rejection_J / accumulated_time_in_seconds / coordination.footprint_area_m2
        coordination.ep_sensWaste_w_m2_per_footprint_area += hvac_waste_w_m2

        time_index_alignment_bool = 1 > abs(curr_sim_time_in_seconds - coordination.vcwg_needed_time_idx_in_seconds)

        if not time_index_alignment_bool:
            coordination.sem2.release()
            return

        roof_Text_C, floor_Text_C, s_wall_Text_c, n_wall_Text_c = _get_sensor_values(state, hanldesDict)

        coordination.ep_floor_Text_K = floor_Text_C + 273.15
        coordination.ep_roof_Text_K = roof_Text_C + 273.15
        coordination.ep_wallSun_Text_K = s_wall_Text_c + 273.15
        coordination.ep_wallShade_Text_K = n_wall_Text_c + 273.15
        coordination.sem3.release()

def run_ep_api():

    experiments_theme = 'Chicago_MedOffice_IDFComplexity'
    epwFileName = 'USA_IL_Chicago-OHare.Intl.AP.725300_TMY3_No_Precipitable_Water.epw'
    idfFileName = 'Detailed_MedOffice.idf'
    TopForcingFileName = 'None'
    VCWGParamFileName = 'Chicago_MedOffice.uwg'
    start_time = '2004-06-01 00:00:00'

    '''
    experiments_theme = 'Chicago_MidRiseApartment_IDFComplexity'
    epwFileName = 'USA_IL_Chicago-OHare.Intl.AP.725300_TMY3_No_Precipitable_Water.epw'
    idfFileName = 'Detailed_MidRiseApartment.idf'
    TopForcingFileName = 'None'
    VCWGParamFileName = 'Chicago_MidRiseApartment.uwg'
    start_time = '2004-06-01 00:00:00'
    '''

    coordination.ini_all(experiments_theme,idfFileName,epwFileName,start_time,
                         TopForcingFileName,VCWGParamFileName)

    state = coordination.ep_api.state_manager.new_state()
    coordination.psychrometric=coordination.ep_api.functional.psychrometrics(state)
    coordination.ep_api.runtime.callback_begin_zone_timestep_before_set_current_weather(state,
                                                                                        overwrite_ep_weather)
    if 'Detailed_MedOffice' in coordination.bld_type or 'Detailed_MidRiseApartment' in coordination.bld_type:
        coordination.ep_api.runtime.callback_end_system_timestep_after_hvac_reporting(state,
                                                                                      medOff_midApart_get_ep_results)
    else:
        raise ValueError('ERROR: Building type not supported')

    coordination.ep_api.exchange.request_variable(state, "HVAC System Total Heat Rejection Energy", "SIMHVAC")
    coordination.ep_api.exchange.request_variable(state, "Site Outdoor Air Drybulb Temperature", "ENVIRONMENT")
    coordination.ep_api.exchange.request_variable(state, "Site Outdoor Air Humidity Ratio", "ENVIRONMENT")

    output_path = coordination.ep_trivial_path
    weather_file_path = os.path.join('.\\resources\\epw', epwFileName)
    idfFilePath = os.path.join(f'.\\resources\\idf', idfFileName)
    sys_args = '-d', output_path, '-w', weather_file_path, idfFilePath
    coordination.ep_api.runtime.run_energyplus(state, sys_args)

if __name__ == '__main__':
    run_ep_api()