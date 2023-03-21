from multiprocessing import Process
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
    ViewFactorFileName = f'{coordination.bld_type }_ViewFactor.txt'
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
def _getMedOffice_roof_actuator_handle(state):
    if 'Detailed_MedOffice' in coordination.bld_type:
        roof_hConv_actuator_handle = coordination.ep_api.exchange. \
            get_actuator_handle(state, "Surface", "Exterior Surface Convection Heat Transfer Coefficient", \
                                "BUILDING_ROOF")
    elif "ShoeBox_MedOffice" in coordination.bld_type:
        roof_hConv_actuator_handle = coordination.ep_api.exchange. \
            get_actuator_handle(state, "Surface", "Exterior Surface Convection Heat Transfer Coefficient", \
                                "Surface 2")
    if roof_hConv_actuator_handle < 0:
        print('get medium office roof actuator handle failed')
        os.getpid()
        os.kill(os.getpid(), signal.SIGTERM)
    return [roof_hConv_actuator_handle]
def _highOfficeGetRoofActuatorHandles(state):
    roofHconv_handles = []
    for roofSurfaceNbr in [576, 582, 588, 594, 600]:
        tmp_handle = coordination.ep_api.exchange. \
            get_actuator_handle(state, "Surface", "Exterior Surface Convection Heat Transfer Coefficient", \
                                f"Surface {roofSurfaceNbr}")
        if tmp_handle < 0:
            print('ovewrite_ep_weather(): HighOffice, roof handle not available')
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)
        roofHconv_handles.append(tmp_handle)
    return roofHconv_handles
def overwrite_ep_weather(state):
    global odb_actuator_handle, orh_actuator_handle,roof_hConv_act_lst

    if not coordination.overwrite_ep_weather_inited_handle:
        if not coordination.ep_api.exchange.api_data_fully_ready(state):
            return
        coordination.overwrite_ep_weather_inited_handle = True
        odb_actuator_handle = coordination.ep_api.exchange.\
            get_actuator_handle(state, "Weather Data", "Outdoor Dry Bulb", "Environment")
        orh_actuator_handle = coordination.ep_api.exchange.\
            get_actuator_handle(state, "Weather Data", "Outdoor Relative Humidity", "Environment")

        if 'MedOffice' in coordination.bld_type:
            roof_hConv_act_lst = _getMedOffice_roof_actuator_handle(state)
        elif 'MidRiseApartment' in coordination.bld_type:
            roof_hConv_act_lst = _get_midRiseApart_roof_actuator_handle(state)
        elif "HighOffice" in coordination.bld_type:
            roof_hConv_act_lst = _highOfficeGetRoofActuatorHandles(state)
        else:
            print('overwrite_ep_weather(): bld_type not supported')
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
            coordination.ep_api.exchange.set_actuator_value(state, roof_hConv_actuator_handle,
                                                            coordination.vcwg_hConv_w_m2_per_K)
        coordination.sem2.release()#
def _medOffice_get_sensor_handles(state):
    handles_dict  = {}
    hvac_heat_rejection_sensor_handle  = \
            coordination.ep_api.exchange.get_variable_handle(state,\
                                                             "HVAC System Total Heat Rejection Energy",\
                                                             "SIMHVAC")
    if 'ShoeBox_MedOffice' in coordination.bld_type:
        roof_Text_handle  = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature", \
                                                                        "Surface 2")
        flr_Text_handle = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature", \
                                                                           "Surface 1")
        s_wall_Text_handle = coordination.ep_api.exchange.get_variable_handle(state, \
                                                                              "Surface Outside Face Temperature", \
                                                                              "Surface 6")
        n_wall_Text_handle = coordination.ep_api.exchange.get_variable_handle(state, \
                                                                              "Surface Outside Face Temperature", \
                                                                              "Surface 3")
        if hvac_heat_rejection_sensor_handle * roof_Text_handle * flr_Text_handle * s_wall_Text_handle * n_wall_Text_handle < 0:
            print("MediumOffice_get_handles: get sensor handles < 0")
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)
        handles_dict['simhvac'] = hvac_heat_rejection_sensor_handle
        handles_dict['roof_Text'] = [roof_Text_handle]
        handles_dict['floor_Text'] = [flr_Text_handle]
        handles_dict['s_wall_Text'] = [s_wall_Text_handle]
        handles_dict['n_wall_Text'] = [n_wall_Text_handle]
        return handles_dict

    roof_Text_handle  = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature", \
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
    for surface  in flr_surfaces:
        _tmp   = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature", \
                                                                        surface )
        if _tmp   < 0:
            print("MediumOffice_get_handles: _tmp < 0")
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)
        handles_dict['floor_Text'].append(_tmp)

    handles_dict['s_wall_Text'] = []
    handles_dict['n_wall_Text'] = []
    _levels = ['bot', 'mid', 'top']
    for level in _levels:
        _tmp_SText = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature", \
                                                                      "Perimeter_" + level + "_ZN_1_Wall_South")
        _tmp_NText = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature", \
                                                                      "Perimeter_" + level + "_ZN_3_Wall_North")
        if _tmp_SText  * _tmp_NText  < 0:
            print("MediumOffice_get_handles: _tmp_SText  * _tmp_NText  < 0")
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)
        handles_dict['s_wall_Text'].append(_tmp_SText)
        handles_dict['n_wall_Text'].append(_tmp_NText)
    return handles_dict

def _medOffice_get_sensor_values(state, handleDict):
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
        if 'MedOffice' in coordination.bld_type:
            hanldesDict = _medOffice_get_sensor_handles(state)
        elif 'Detailed_MidRiseApartment' in coordination.bld_type:
            hanldesDict = _midRiseApar_get_sensor_handles(state)

    # get EP results, upload to coordination
    if coordination.called_vcwg_bool:

        coordination.sem2.acquire()
        curr_sim_time_in_hours = coordination.ep_api.exchange.current_sim_time(state)
        curr_sim_time_in_seconds = curr_sim_time_in_hours * 3600  # Should always accumulate, since system time always advances
        accumulated_time_in_seconds = curr_sim_time_in_seconds - coordination.ep_last_call_time_seconds
        coordination.ep_last_call_time_seconds = curr_sim_time_in_seconds
        hvac_heat_rejection_J = coordination.ep_api.exchange.get_variable_value(state, hanldesDict['simhvac'])
        hvac_waste_w_m2 = hvac_heat_rejection_J / accumulated_time_in_seconds / coordination.footprint_area_m2
        coordination.ep_sensWaste_w_m2_per_footprint_area += hvac_waste_w_m2

        time_index_alignment_bool = 1 > abs(curr_sim_time_in_seconds - coordination.vcwg_needed_time_idx_in_seconds)

        if not time_index_alignment_bool:
            coordination.sem2.release()
            return

        roof_Text_C, floor_Text_C, s_wall_Text_c, n_wall_Text_c = _medOffice_get_sensor_values(state, hanldesDict)

        coordination.ep_floor_Text_K = floor_Text_C + 273.15
        coordination.ep_roof_Text_K = roof_Text_C + 273.15
        coordination.ep_wallSun_Text_K = s_wall_Text_c + 273.15
        coordination.ep_wallShade_Text_K = n_wall_Text_c + 273.15
        coordination.sem3.release()
def _highOffice_get_sensor_handles(state):
    '''
        surface576_roof_Text_c_handle, surface582_roof_Text_c_handle, surface588_roof_Text_c_handle, \
        surface594_roof_Text_c_handle, surface600_roof_Text_c_handle, surface1_floor_Text_c_handle, \
        surface7_floor_Text_c_handle, surface13_floor_Text_c_handle, surface19_floor_Text_c_handle, \
        surface25_floor_Text_c_handle

        surface92_south_wall_Text_c_handle, surface122_south_wall_Text_c_handle, surface152_south_wall_Text_c_handle, \
        surface182_south_wall_Text_c_handle, surface212_south_wall_Text_c_handle, surface242_south_wall_Text_c_handle, \
        surface272_south_wall_Text_c_handle, surface302_south_wall_Text_c_handle, surface332_south_wall_Text_c_handle, \
        surface362_south_wall_Text_c_handle, surface392_south_wall_Text_c_handle, surface422_south_wall_Text_c_handle, \
        surface452_south_wall_Text_c_handle, surface482_south_wall_Text_c_handle, surface512_south_wall_Text_c_handle, \
        surface542_south_wall_Text_c_handle, surface572_south_wall_Text_c_handle,\
        surface26_north_wall_Text_c_handle, surface56_north_wall_Text_c_handle, surface86_north_wall_Text_c_handle, \
        surface116_north_wall_Text_c_handle, surface146_north_wall_Text_c_handle, surface176_north_wall_Text_c_handle, \
        surface206_north_wall_Text_c_handle, surface236_north_wall_Text_c_handle, surface266_north_wall_Text_c_handle, \
        surface296_north_wall_Text_c_handle, surface326_north_wall_Text_c_handle, surface356_north_wall_Text_c_handle, \
        surface386_north_wall_Text_c_handle, surface416_north_wall_Text_c_handle, surface446_north_wall_Text_c_handle, \
        surface476_north_wall_Text_c_handle, surface506_north_wall_Text_c_handle, surface536_north_wall_Text_c_handle, \
        surface566_north_wall_Text_c_handle, surface596_north_wall_Text_c_handle,\
        surface14_east_wall_Text_c_handle, surface44_east_wall_Text_c_handle, surface74_east_wall_Text_c_handle, \
        surface104_east_wall_Text_c_handle, surface134_east_wall_Text_c_handle, surface164_east_wall_Text_c_handle, \
        surface194_east_wall_Text_c_handle, surface224_east_wall_Text_c_handle, surface254_east_wall_Text_c_handle, \
        surface284_east_wall_Text_c_handle, surface314_east_wall_Text_c_handle, surface344_east_wall_Text_c_handle, \
        surface374_east_wall_Text_c_handle, surface404_east_wall_Text_c_handle, surface434_east_wall_Text_c_handle, \
        surface464_east_wall_Text_c_handle, surface494_east_wall_Text_c_handle, surface524_east_wall_Text_c_handle, \
        surface554_east_wall_Text_c_handle, surface584_east_wall_Text_c_handle,\
        surface10_west_wall_Text_c_handle, surface40_west_wall_Text_c_handle, surface70_west_wall_Text_c_handle, \
        surface100_west_wall_Text_c_handle, surface130_west_wall_Text_c_handle, surface160_west_wall_Text_c_handle, \
        surface190_west_wall_Text_c_handle, surface220_west_wall_Text_c_handle, surface250_west_wall_Text_c_handle, \
        surface280_west_wall_Text_c_handle, surface310_west_wall_Text_c_handle, surface340_west_wall_Text_c_handle, \
        surface370_west_wall_Text_c_handle, surface400_west_wall_Text_c_handle, surface430_west_wall_Text_c_handle, \
        surface460_west_wall_Text_c_handle, surface490_west_wall_Text_c_handle, surface520_west_wall_Text_c_handle, \
        surface550_west_wall_Text_c_handle, surface580_west_wall_Text_c_handle
    '''
    roof_floor_handles_dict = {}
    roof_floor_handles_dict['roof'] = []
    roof_floor_handles_dict['floor'] = []
    for i in range(1, 6):
        tmp_roof = coordination.ep_api.exchange.get_variable_handle(state,
                                                                    "Surface Outside Face Temperature",
                                                                    "Surface " + str(576 + (i - 1) * 6))
        tmp_floor = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature",
                                                                     "Surface " + str(1 + (i - 1) * 6))
        if tmp_roof * tmp_floor < 0:
            print("20 Stories roof or floor surface handle error!")
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)

        roof_floor_handles_dict['roof'].append(tmp_roof)
        roof_floor_handles_dict['floor'].append(tmp_floor)

    wall_handles_dict = {}
    wall_handles_dict['south'] = []
    wall_handles_dict['north'] = []

    if 'Simplified_HighOffice' in coordination.bld_type:
        flr_nbrs = [1,11,20]
    else:
        flr_nbrs = [ i for i in range(1,21)]

    for i in flr_nbrs:
        tmp_south = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature", \
                                                                                                "Surface " + str(2 + (i - 1) * 30))
        tmp_north = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature", \
                                                                                                "Surface " + str(26 + (i - 1) * 30))
        if tmp_south * tmp_north < 0:
            print("20 Stories wall surface handle error!")
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)

        wall_handles_dict['south'].append(tmp_south)
        wall_handles_dict['north'].append(tmp_north)

    return wall_handles_dict, roof_floor_handles_dict

def _highOffice_get_sensor_values(state, wall_handles_dict, roof_floor_handles_dict):
    #coordination.ep_api.exchange.get_variable_value(state, surface576_roof_Text_c_handle)
    wall_temperatures_dict = {}
    wall_temperatures_dict['south'] = []
    wall_temperatures_dict['north'] = []

    for key in ['south', 'north']:
        for i in range(len(wall_handles_dict[key])):
            tmp = coordination.ep_api.exchange.get_variable_value(state, wall_handles_dict[key][i]) + 273.15
            wall_temperatures_dict[key].append(tmp)
    south_wall_Text_K = 0
    north_wall_Text_K = 0
    for i in range(len(wall_temperatures_dict['south'])):
        south_wall_Text_K += wall_temperatures_dict['south'][i]
        north_wall_Text_K += wall_temperatures_dict['north'][i]
    south_wall_Text_K /= len(wall_temperatures_dict['south'])
    north_wall_Text_K /= len(wall_temperatures_dict['north'])

    roof_Text_K = 0
    floor_Text_K = 0
    for i in range(len(roof_floor_handles_dict['roof'])):
        roof_Text_K += coordination.ep_api.exchange.get_variable_value(state, roof_floor_handles_dict['roof'][i]) + 273.15
        floor_Text_K += coordination.ep_api.exchange.get_variable_value(state, roof_floor_handles_dict['floor'][i]) + 273.15
    roof_Text_K /= len(roof_floor_handles_dict['roof'])
    floor_Text_K /= len(roof_floor_handles_dict['floor'])

    return roof_Text_K, floor_Text_K, south_wall_Text_K, north_wall_Text_K
def high20Stories_get_ep_results(state):
    global hvac_heat_rejection_sensor_handle,\
        wall_handles_dict, roof_floor_handles_dict
    if not coordination.get_ep_results_inited_handle:
        if not coordination.ep_api.exchange.api_data_fully_ready(state):
            return
        coordination.get_ep_results_inited_handle = True
        wall_handles_dict,roof_floor_handles_dict = _highOffice_get_sensor_handles(state)
        hvac_heat_rejection_sensor_handle = \
            coordination.ep_api.exchange.get_variable_handle(state,\
                                                             "HVAC System Total Heat Rejection Energy",\
                                                             "SIMHVAC")
    warm_up = coordination.ep_api.exchange.warmup_flag(state)
    if not warm_up and coordination.called_vcwg_bool:
        coordination.sem2.acquire()
        curr_sim_time_in_hours = coordination.ep_api.exchange.current_sim_time(state)
        curr_sim_time_in_seconds = curr_sim_time_in_hours * 3600  # Should always accumulate, since system time always advances
        accumulated_time_in_seconds = curr_sim_time_in_seconds - coordination.ep_last_call_time_seconds
        coordination.ep_last_call_time_seconds = curr_sim_time_in_seconds
        hvac_heat_rejection_J = coordination.ep_api.exchange.get_variable_value(state,hvac_heat_rejection_sensor_handle)
        hvac_waste_w_m2 = hvac_heat_rejection_J / accumulated_time_in_seconds / coordination.footprint_area_m2
        coordination.ep_sensWaste_w_m2_per_footprint_area += hvac_waste_w_m2

        time_index_alignment_bool = 1 > abs(curr_sim_time_in_seconds - coordination.vcwg_needed_time_idx_in_seconds)
        if not time_index_alignment_bool:
            coordination.sem2.release()
            return

        print(f'coordination.ep_sensWaste_w_m2_per_footprint_area = '
              f'{coordination.ep_sensWaste_w_m2_per_footprint_area},')

        roof_Text_K, floor_Text_K, south_wall_Text_K, north_wall_Text_K \
            = _highOffice_get_sensor_values(state, wall_handles_dict, roof_floor_handles_dict)

        coordination.ep_floor_Text_K = floor_Text_K
        coordination.ep_roof_Text_K = roof_Text_K
        coordination.ep_wallSun_Text_K = south_wall_Text_K
        coordination.ep_wallShade_Text_K = north_wall_Text_K

        coordination.sem3.release()

def run_ep_api(idfFileName,VCWGParamFileName):

    TopForcingFileName = 'None'
    epwFileName = 'USA_IL_Chicago-OHare.Intl.AP.725300_TMY3_No_Precipitable_Water.epw'
    start_time = '2004-06-01 00:00:00'
    experiments_theme = idfFileName[:-4]
    coordination.ini_all(experiments_theme,idfFileName,epwFileName,start_time,
                            TopForcingFileName,VCWGParamFileName)
    state = coordination.ep_api.state_manager.new_state()
    coordination.psychrometric=coordination.ep_api.functional.psychrometrics(state)
    coordination.ep_api.runtime.callback_begin_zone_timestep_before_set_current_weather(state,
                                                                                        overwrite_ep_weather)
    if 'MedOffice' in coordination.bld_type or 'Detailed_MidRiseApartment' in coordination.bld_type:
        coordination.ep_api.runtime.callback_end_system_timestep_after_hvac_reporting(state,
                                                                                      medOff_midApart_get_ep_results)
    elif 'HighOffice' in coordination.bld_type:
        coordination.ep_api.runtime.callback_end_system_timestep_after_hvac_reporting(state,
                                                                                      high20Stories_get_ep_results)
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

    # idfFileName = 'Scalar_Detailed_HighOffice.idf'
    # VCWGParamFileName = 'Dummy_Chicago_20Stories.uwg'

    '''
    idfFileName = 'Scalar_Simplified_HighOffice.idf'
    VCWGParamFileName = 'Dummy_Chicago_20Stories.uwg'
    '''

    # idfFileName = 'Scalar_Detailed_MedOffice.idf'
    # VCWGParamFileName = 'Chicago_MedOffice.uwg'

    # idfFileName = 'Scalar_ShoeBox_MedOffice.idf'
    # VCWGParamFileName = 'Chicago_MedOffice.uwg'

    # idfFileName = 'Scalar_Detailed_MidRiseApartment.idf'
    # VCWGParamFileName = 'Chicago_MidRiseApartment.uwg'
    groups = [
        # ['Scalar_Detailed_HighOffice.idf', 'Dummy_Chicago_20Stories.uwg'],
        ['Scalar_Simplified_HighOffice.idf', 'Dummy_Chicago_20Stories.uwg'],
        # ['Scalar_Detailed_MedOffice.idf', 'Chicago_MedOffice.uwg'],
        # ['Scalar_ShoeBox_MedOffice.idf', 'Chicago_MedOffice.uwg'],
        # ['Scalar_Detailed_MidRiseApartment.idf', 'Chicago_MidRiseApartment.uwg']
    ]
    _jobs = []
    for group in groups:
        _temP = Process(target=run_ep_api, args=(group[0], group[1]))
        _jobs.append(_temP)

    for job in _jobs:
        job.start()
    for job in _jobs:
        job.join()