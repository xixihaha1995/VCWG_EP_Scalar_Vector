from multiprocessing import Process
from threading import Thread
import _1_parent_coordination as coordination
from VCWG_Hydrology import VCWG_Hydro
import os, signal
def api_to_csv(state):
    orig = coordination.ep_api.exchange.list_available_api_data_csv(state)
    newFileByteArray = bytearray(orig)
    api_path = os.path.join(os.path.dirname(__file__), 'api_data.csv')
    newFile = open(api_path, "wb")
    newFile.write(newFileByteArray)
    newFile.close()
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
def _to_get_wet_bulb(state, dry_bulb_temp_C, humidity_ratio, barometric_pressure_Pa):
    _wetbulb = coordination.psychrometric.wet_bulb(state, dry_bulb_temp_C, humidity_ratio, barometric_pressure_Pa)
    return _wetbulb

def _medOfficeGetAirNodeHandles(state):
    flrs = ['BOT', 'MID', 'TOP']
    handles = {}
    handles['odb'] = []
    handles['owb'] = []
    for flr in flrs:
        tmp_odb_handle = coordination.ep_api.exchange. \
            get_actuator_handle(state, "Schedule:Compact", "Schedule Value", f"OUTDOORAIRNODE:{flr}DRYBULB")
        tmp_owb_handle = coordination.ep_api.exchange. \
            get_actuator_handle(state, "Schedule:Compact", "Schedule Value", f"OUTDOORAIRNODE:{flr}WETBULB")
        if tmp_odb_handle <0 or tmp_owb_handle < 0:
            print('ovewrite_ep_weather(): Detailed_MedOffice,some handle not available')
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)
        handles['odb'].append(tmp_odb_handle)
        handles['owb'].append(tmp_owb_handle)
    return handles

def _highOfficeGetActuatorHandles(state):
    handles = {}
    handles['roofHconv'] = []
    if '20Stories' in coordination.bld_type:
        flr_nbrs = [i for i in range(1, 21)]
    elif 'SimplifiedHighBld' in coordination.bld_type:
        flr_nbrs = [1, 11, 20]
    for roofSurfaceNbr in [576, 582, 588, 594, 600]:
        tmp_handle = coordination.ep_api.exchange. \
            get_actuator_handle(state, "Surface", "Exterior Surface Convection Heat Transfer Coefficient", \
                                f"Surface {roofSurfaceNbr}")
        if tmp_handle < 0:
            print('ovewrite_ep_weather(): HighOffice, roof handle not available')
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)
        handles['roofHconv'].append(tmp_handle)

    for flr in flr_nbrs:
        tmp_odb_handle = coordination.ep_api.exchange. \
            get_actuator_handle(state, "Schedule:Compact", "Schedule Value", f"OUTDOORAIRNODE:Floor_{flr}DryBulb")
        tmp_owb_handle = coordination.ep_api.exchange. \
            get_actuator_handle(state, "Schedule:Compact", "Schedule Value", f"OUTDOORAIRNODE:Floor_{flr}WetBulb")
        if tmp_odb_handle <0 or tmp_owb_handle < 0:
            print('ovewrite_ep_weather(): HighOffice, some OAT handle not available')
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)
        handles[f'odb{flr}'] = tmp_odb_handle
        handles[f'owb{flr}'] = tmp_owb_handle
    return handles
def overwrite_ep_weather(state):
    global odb_actuator_handle, orh_actuator_handle,roof_hConv_act_lst,\
        wsped_mps_actuator_handle, wdir_deg_actuator_handle,zone_flr_area_handle

    if not coordination.overwrite_ep_weather_inited_handle:
        if not coordination.ep_api.exchange.api_data_fully_ready(state):
            return
        # api_to_csv(state)
        coordination.overwrite_ep_weather_inited_handle = True
        odb_actuator_handle = coordination.ep_api.exchange.\
            get_actuator_handle(state, "Weather Data", "Outdoor Dry Bulb", "Environment")
        orh_actuator_handle = coordination.ep_api.exchange.\
            get_actuator_handle(state, "Weather Data", "Outdoor Relative Humidity", "Environment")

        if 'Detailed_MedOffice' in coordination.bld_type:
            global medOdbOwbHandles
            medOdbOwbHandles = _medOfficeGetAirNodeHandles(state)
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
        if "20Stories" in coordination.bld_type or 'SimplifiedHighBld' in coordination.bld_type:
            global highOfficeActuatorsHandles
            highOfficeActuatorsHandles = _highOfficeGetActuatorHandles(state)
        if odb_actuator_handle <0 or orh_actuator_handle< 0:
            print('ovewrite_ep_weather(): some handle not available')
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
        odb_c_list = [i - 273.15 for i in coordination.vcwg_canTemp_K_list]
        owb_c_list = [_to_get_wet_bulb(state, i, coordination.vcwg_canSpecHum_Ratio_list[odb_c_list.index(i)],
                                       coordination.vcwg_canPress_Pa_list[odb_c_list.index(i)]) for i in odb_c_list]
        if "Detailed_MedOffice" in coordination.bld_type:
            for roof_hConv_actuator_handle in roof_hConv_act_lst:
                coordination.ep_api.exchange.set_actuator_value(state, roof_hConv_actuator_handle,coordination.vcwg_hConv_w_m2_per_K)
            for idx in range(len(odb_c_list)):
                coordination.ep_api.exchange.set_actuator_value(state, medOdbOwbHandles['odb'][idx], odb_c_list[idx])
                coordination.ep_api.exchange.set_actuator_value(state, medOdbOwbHandles['owb'][idx], owb_c_list[idx])

        elif "20Stories" in coordination.bld_type or "SimplifiedHighBld" in coordination.bld_type:
            if '20Stories' in coordination.bld_type:
                flr_nbrs = [i for i in range(1, 21)]
            elif 'SimplifiedHighBld' in coordination.bld_type:
                flr_nbrs = [1, 11, 20]
            coordination.save_canyon_odb_c = coordination.vcwg_canTemp_K - 273.15
            coordination.save_canyon_rh_percent = rh
            coordination.save_floor_odb_c = odb_c_list
            coordination.save_floor_owb_c = owb_c_list
            print(f'{coordination.bld_type}, odb_c_list: {odb_c_list}')
            # for rofHans in highOfficeActuatorsHandles['roofHconv']:
            #     coordination.ep_api.exchange.set_actuator_value(state, rofHans, coordination.vcwg_hConv_w_m2_per_K)
            for idx, flr_nbr in enumerate(flr_nbrs):
                coordination.ep_api.exchange.set_actuator_value(state, highOfficeActuatorsHandles[f'odb{flr_nbr}'],
                                                                odb_c_list[idx])
                coordination.ep_api.exchange.set_actuator_value(state, highOfficeActuatorsHandles[f'owb{flr_nbr}'],
                                                                owb_c_list[idx])
        coordination.sem2.release()#
def _medium_get_sensor_handles(state):
    handles_dict  = {}
    hvac_heat_rejection_sensor_handle  = \
            coordination.ep_api.exchange.get_variable_handle(state,\
                                                             "HVAC System Total Heat Rejection Energy",\
                                                             "SIMHVAC")
    roof_Text_handle  = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature", \
                                                                        "Building_Roof")
    if hvac_heat_rejection_sensor_handle <0 or roof_Text_handle < 0:
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
        if _tmp_SText <0 or _tmp_SSolar <0 or _tmp_NText <0 or _tmp_NSolar < 0:
            print("MediumOffice_get_handles: _tmp_SText * _tmp_SSolar * _tmp_NText * _tmp_NSolar < 0")
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)
        handles_dict['s_wall_Text'].append(_tmp_SText)
        handles_dict['s_wall_Solar'].append(_tmp_SSolar)
        handles_dict['n_wall_Text'].append(_tmp_NText)
        handles_dict['n_wall_Solar'].append(_tmp_NSolar)
    return handles_dict

def _medOffice_get_sensor_values(state, handleDict):
    _roof_Text_c = 0
    _floor_Text_c = 0
    _s_wall_Text_c = 0
    _s_wall_Solar_w_m2 = 0
    _n_wall_Text_c = 0
    _n_wall_Solar_w_m2 = 0
    wall_temperatures_dict = {}
    wall_temperatures_dict['south'] = []
    wall_temperatures_dict['north'] = []

    for i in range(len(handleDict['roof_Text'])):
        _roof_Text_c += coordination.ep_api.exchange.get_variable_value(state, handleDict['roof_Text'][i])
    for i in range(len(handleDict['floor_Text'])):
        _floor_Text_c += coordination.ep_api.exchange.get_variable_value(state, handleDict['floor_Text'][i])

    for i in range(len(handleDict['s_wall_Text'])):
        _s_wall_Text_c += coordination.ep_api.exchange.get_variable_value(state, handleDict['s_wall_Text'][i])
        _n_wall_Text_c += coordination.ep_api.exchange.get_variable_value(state, handleDict['n_wall_Text'][i])
        _south_C = coordination.ep_api.exchange.get_variable_value(state, handleDict['s_wall_Text'][i])
        _north_C = coordination.ep_api.exchange.get_variable_value(state, handleDict['n_wall_Text'][i])
        wall_temperatures_dict['south'].append(_south_C+273.15)
        wall_temperatures_dict['north'].append(_north_C+273.15)

    _roof_Text_c /= len(handleDict['roof_Text'])
    _floor_Text_c /= len(handleDict['floor_Text'])
    _s_wall_Text_c /= len(handleDict['s_wall_Text'])
    _n_wall_Text_c /= len(handleDict['n_wall_Text'])
    coordination.EP_wall_temperatures_K_dict = wall_temperatures_dict
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

    # get EP results, upload to coordination
    if coordination.called_vcwg_bool:

        coordination.sem2.acquire()
        curr_sim_time_in_hours = coordination.ep_api.exchange.current_sim_time(state)
        curr_sim_time_in_seconds = curr_sim_time_in_hours * 3600  # Should always accumulate, since system time always advances
        accumulated_time_in_seconds = curr_sim_time_in_seconds - coordination.ep_last_call_time_seconds
        coordination.ep_last_call_time_seconds = curr_sim_time_in_seconds
        hvac_heat_rejection_J = coordination.ep_api.exchange.get_variable_value(state, hanldesDict['simhvac'])
        hvac_waste_w_m2 = hvac_heat_rejection_J / accumulated_time_in_seconds / coordination.footprint_area_m2
        for flr in range(coordination.EP_nFloor):
            coordination.EP_floor_energy_lst[flr] += hvac_waste_w_m2 / coordination.EP_nFloor
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


def _20Stories_get_zone_to_pthp_dict():
    global zone_pthp_dict
    zone_pthp_dict = {}
    zone_pthp_dict[1] = 56
    zone_pthp_dict[10] = 65
    zone_pthp_dict[100] = 6
    zone_pthp_dict[11] = 66
    zone_pthp_dict[12] = 67
    zone_pthp_dict[13] = 68
    zone_pthp_dict[14] = 69
    zone_pthp_dict[15] = 70
    zone_pthp_dict[16] = 71
    zone_pthp_dict[17] = 72
    zone_pthp_dict[18] = 73
    zone_pthp_dict[19] = 74
    zone_pthp_dict[2] = 57
    zone_pthp_dict[20] = 75
    zone_pthp_dict[21] = 76
    zone_pthp_dict[22] = 77
    zone_pthp_dict[23] = 78
    zone_pthp_dict[24] = 79
    zone_pthp_dict[25] = 80
    zone_pthp_dict[26] = 81
    zone_pthp_dict[27] = 82
    zone_pthp_dict[28] = 83
    zone_pthp_dict[29] = 84
    zone_pthp_dict[3] = 58
    zone_pthp_dict[30] = 85
    zone_pthp_dict[31] = 86
    zone_pthp_dict[32] = 87
    zone_pthp_dict[33] = 88
    zone_pthp_dict[34] = 89
    zone_pthp_dict[35] = 90
    zone_pthp_dict[36] = 91
    zone_pthp_dict[37] = 92
    zone_pthp_dict[38] = 93
    zone_pthp_dict[39] = 94
    zone_pthp_dict[4] = 59
    zone_pthp_dict[40] = 95
    zone_pthp_dict[41] = 96
    zone_pthp_dict[42] = 97
    zone_pthp_dict[43] = 98
    zone_pthp_dict[44] = 99
    zone_pthp_dict[45] = 100
    zone_pthp_dict[46] = 38
    zone_pthp_dict[47] = 39
    zone_pthp_dict[48] = 40
    zone_pthp_dict[49] = 41
    zone_pthp_dict[5] = 60
    zone_pthp_dict[50] = 42
    zone_pthp_dict[51] = 43
    zone_pthp_dict[52] = 44
    zone_pthp_dict[53] = 45
    zone_pthp_dict[54] = 46
    zone_pthp_dict[55] = 47
    zone_pthp_dict[56] = 48
    zone_pthp_dict[57] = 49
    zone_pthp_dict[58] = 50
    zone_pthp_dict[59] = 51
    zone_pthp_dict[6] = 61
    zone_pthp_dict[60] = 52
    zone_pthp_dict[61] = 53
    zone_pthp_dict[62] = 54
    zone_pthp_dict[63] = 55
    zone_pthp_dict[64] = 36
    zone_pthp_dict[65] = 37
    zone_pthp_dict[66] = 34
    zone_pthp_dict[67] = 35
    zone_pthp_dict[68] = 25
    zone_pthp_dict[69] = 26
    zone_pthp_dict[7] = 62
    zone_pthp_dict[70] = 27
    zone_pthp_dict[71] = 28
    zone_pthp_dict[72] = 29
    zone_pthp_dict[73] = 30
    zone_pthp_dict[74] = 31
    zone_pthp_dict[75] = 32
    zone_pthp_dict[76] = 33
    zone_pthp_dict[77] = 23
    zone_pthp_dict[78] = 24
    zone_pthp_dict[79] = 18
    zone_pthp_dict[8] = 63
    zone_pthp_dict[80] = 19
    zone_pthp_dict[81] = 20
    zone_pthp_dict[82] = 21
    zone_pthp_dict[83] = 22
    zone_pthp_dict[84] = 16
    zone_pthp_dict[85] = 17
    zone_pthp_dict[86] = 14
    zone_pthp_dict[87] = 15
    zone_pthp_dict[88] = 12
    zone_pthp_dict[89] = 13
    zone_pthp_dict[9] = 64
    zone_pthp_dict[90] = 11
    zone_pthp_dict[91] = 7
    zone_pthp_dict[92] = 8
    zone_pthp_dict[93] = 9
    zone_pthp_dict[94] = 10
    zone_pthp_dict[95] = 1
    zone_pthp_dict[96] = 2
    zone_pthp_dict[97] = 3
    zone_pthp_dict[98] = 4
    zone_pthp_dict[99] = 5


def _20Stories_batch_get_energy_results(state, dict, accumulated_time_in_seconds):
    '''
    Zone Packaged Terminal Heat Pump Total Heating Energy
    Zone Packaged Terminal Heat Pump Total Cooling Energy
    Zone Packaged Terminal Heat Pump Electricity Energy
    'PTHP 1' ... 'PTHP 100'
    '''

    if 'SimplifiedHighBld' in coordination.bld_type:
        flr_nbrs = [1,11,20]
    else:
        flr_nbrs = [ i for i in range(1,21)]
    zone_nbrs = [(i - 1) * 5 + j for i in flr_nbrs for j in range(1, 6)]

    energy_dict = {}
    heating_total = 0
    cooling_total = 0
    electricity_total = 0
    for tmp_zone_nbr in zone_nbrs:
        i = zone_pthp_dict[tmp_zone_nbr]
        energy_dict['PTHP ' + str(i)] = []
        tmp_heating = coordination.ep_api.exchange.get_variable_value(state, dict['PTHP ' + str(i)][0])
        tmp_cooling = coordination.ep_api.exchange.get_variable_value(state, dict['PTHP ' + str(i)][1])
        tmp_electricity = coordination.ep_api.exchange.get_variable_value(state, dict['PTHP ' + str(i)][2])
        energy_dict['PTHP ' + str(i)].append(tmp_heating)
        energy_dict['PTHP ' + str(i)].append(tmp_cooling)
        energy_dict['PTHP ' + str(i)].append(tmp_electricity)
        heating_total += tmp_heating
        cooling_total += tmp_cooling
        electricity_total += tmp_electricity

    for idx, i in enumerate(flr_nbrs):
        for j in range(1, 6):
            tmp_zone = zone_pthp_dict[(i - 1) * 5 + j]
            # coordination.EP_floor_energy_lst[i-1] += energy_dict['PTHP ' + str(tmp_zone)][0]
            coordination.EP_floor_energy_lst[idx] += energy_dict['PTHP ' + str(tmp_zone)][1]
            coordination.EP_floor_energy_lst[idx] += energy_dict['PTHP ' + str(tmp_zone)][2]
        coordination.EP_floor_energy_lst[idx] /= coordination.footprint_area_m2
        coordination.EP_floor_energy_lst[idx] /= accumulated_time_in_seconds
    return energy_dict, heating_total, cooling_total, electricity_total

def _20Stories_batch_handles(state):
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
        if tmp_roof <0 or tmp_floor < 0:
            print("20 Stories roof or floor surface handle error!")
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)

        roof_floor_handles_dict['roof'].append(tmp_roof)
        roof_floor_handles_dict['floor'].append(tmp_floor)

    wall_handles_dict = {}
    wall_handles_dict['south'] = []
    wall_handles_dict['north'] = []
    wall_handles_dict['east'] = []
    wall_handles_dict['west'] = []

    if 'SimplifiedHighBld' in coordination.bld_type:
        flr_nbrs = [1,11,20]
    else:
        flr_nbrs = [ i for i in range(1,21)]
    zone_nbrs = [(i - 1) * 5 + j for i in flr_nbrs for j in range(1, 6)]

    for i in flr_nbrs:
        tmp_south = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature", \
                                                                                                "Surface " + str(2 + (i - 1) * 30))
        tmp_north = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature", \
                                                                                                "Surface " + str(26 + (i - 1) * 30))
        tmp_east = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature", \
                                                                                                "Surface " + str(14 + (i - 1) * 30))
        tmp_west = coordination.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature", \
                                                                                                "Surface " + str(10 + (i - 1) * 30))
        if tmp_south <0 or tmp_west <0 or tmp_east <0 or tmp_north < 0:
            print("20 Stories wall surface handle error!")
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)

        wall_handles_dict['south'].append(tmp_south)
        wall_handles_dict['north'].append(tmp_north)
        wall_handles_dict['east'].append(tmp_east)
        wall_handles_dict['west'].append(tmp_west)

    pthp_dict = {}
    for tmp_zone in zone_nbrs:
        i = zone_pthp_dict[tmp_zone]
        pthp_dict['PTHP ' + str(i)] = []

        _tmpHeating = coordination.ep_api.exchange.get_variable_handle(state,
                                                             "Zone Packaged Terminal Heat Pump Total Heating Energy",
                                                             'PTHP ' + str(i))
        _tmpCooling = coordination.ep_api.exchange.get_variable_handle(state,
                                                             "Zone Packaged Terminal Heat Pump Total Cooling Energy",
                                                             'PTHP ' + str(i))
        _tmpElectricity = coordination.ep_api.exchange.get_variable_handle(state,
                                                           "Zone Packaged Terminal Heat Pump Electricity Energy",
                                                             'PTHP ' + str(i))
        if _tmpHeating <0 or _tmpCooling <0 or  _tmpElectricity < 0:
            print("PTHP energy handle error!")
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)
        pthp_dict['PTHP ' + str(i)].append(_tmpHeating)
        pthp_dict['PTHP ' + str(i)].append(_tmpCooling)
        pthp_dict['PTHP ' + str(i)].append(_tmpElectricity)
    return wall_handles_dict, roof_floor_handles_dict, pthp_dict

def _20_Stories_batch_get_surface_temperatures(state, wall_handles_dict, roof_floor_handles_dict):
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

    return wall_temperatures_dict, roof_Text_K, floor_Text_K, south_wall_Text_K, north_wall_Text_K
def High20Stories_get_ep_results(state):
    global hvac_heat_rejection_sensor_handle,\
        wall_handles_dict, roof_floor_handles_dict, pthp_energy_handles_dict
    _20Stories_get_zone_to_pthp_dict()
    if not coordination.get_ep_results_inited_handle:
        if not coordination.ep_api.exchange.api_data_fully_ready(state):
            return
        coordination.get_ep_results_inited_handle = True
        wall_handles_dict,roof_floor_handles_dict, pthp_energy_handles_dict = _20Stories_batch_handles(state)
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
        pthp_energy_dict, pthp_heating_total, pthp_cooling_total, pthp_electricity_total =\
            _20Stories_batch_get_energy_results(state, pthp_energy_handles_dict, accumulated_time_in_seconds)

        time_index_alignment_bool = 1 > abs(curr_sim_time_in_seconds - coordination.vcwg_needed_time_idx_in_seconds)
        if not time_index_alignment_bool:
            coordination.sem2.release()
            return

        print(f'coordination.ep_sensWaste_w_m2_per_footprint_area = {coordination.ep_sensWaste_w_m2_per_footprint_area},'
              f'coordination.EP_floor_energy_lst = {sum(coordination.EP_floor_energy_lst)}')

        coordination.EP_wall_temperatures_K_dict,roof_Text_K, floor_Text_K, south_wall_Text_K, north_wall_Text_K \
            = _20_Stories_batch_get_surface_temperatures(state, wall_handles_dict, roof_floor_handles_dict)

        coordination.ep_floor_Text_K = floor_Text_K
        coordination.ep_roof_Text_K = roof_Text_K
        coordination.ep_wallSun_Text_K = south_wall_Text_K
        coordination.ep_wallShade_Text_K = north_wall_Text_K

        coordination.sem3.release()

def run_ep_api(experiments_theme, idfFileName, VCWGParamFileName):

    epwFileName = 'USA_IL_Chicago-OHare.Intl.AP.725300_TMY3_No_Precipitable_Water.epw'
    start_time = '2004-06-01 00:00:00'
    TopForcingFileName = 'None'

    coordination.ini_all(experiments_theme,idfFileName,epwFileName,start_time,
                            TopForcingFileName,VCWGParamFileName)
    state = coordination.ep_api.state_manager.new_state()
    coordination.psychrometric=coordination.ep_api.functional.psychrometrics(state)
    coordination.ep_api.runtime.callback_begin_zone_timestep_before_set_current_weather(state,
                                                                                        overwrite_ep_weather)
    if 'Detailed_MedOffice' in coordination.bld_type or 'Detailed_MidRiseApartment' in coordination.bld_type:
        coordination.ep_api.runtime.callback_end_system_timestep_after_hvac_reporting(state,
                                                                                      medOff_midApart_get_ep_results)
    elif '20Stories' in coordination.bld_type or 'SimplifiedHighBld' in coordination.bld_type:
        coordination.ep_api.runtime.callback_end_system_timestep_after_hvac_reporting(state,
                                                                                      High20Stories_get_ep_results)
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
    # idfFileName = 'Vector_Detailed_MedOffice.idf'
    # experiments_theme = 'DummyChicagoMedOffice_The_Effect_sensWaste_Profile'
    # TopForcingFileName = 'None'
    # VCWGParamFileName = 'Chicago_MedOffice.uwg'
    # start_time = '2004-06-01 00:00:00'

    experiments_theme = 'one-way-DummyChicago20Stories_The_Effect_sensWaste_Profile'
    VCWGParamFileName = 'Dummy_Chicago_20Stories.uwg'
    _processes = []
    # ''
    jobs = [
        'Vector_Detailed_20Stories.idf',
        'Vector_SimplifiedHighBld.idf'
            ]
    for idfFileName in jobs:
        _temP = Process(target=run_ep_api, args=(experiments_theme, idfFileName, VCWGParamFileName))
        _processes.append(_temP)

    for _temP in _processes:
        _temP.start()
    for _temP in _processes:
        _temP.join()