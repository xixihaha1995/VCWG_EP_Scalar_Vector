import configparser, datetime, threading, sys, os,numpy

def ini_all(_experiments_theme,_idfFileName,_epwFileName,_start_time,
            _TopForcingFileName,_VCWGParamFileName):
    global config, save_path_clean,ep_trivial_path, data_saving_path, bld_type,\
        ep_api, psychrometric,\
        sem0, sem1, sem2, sem3, \
        vcwg_needed_time_idx_in_seconds, \
        vcwg_canTemp_K, vcwg_canSpecHum_Ratio, vcwg_canPress_Pa, ep_sensWaste_w_m2_per_footprint_area, \
        ep_floor_Text_K, ep_floor_Tint_K, ep_roof_Text_K, ep_roof_Tint_K, \
        ep_wallSun_Text_K, ep_wallSun_Tint_K, ep_wallShade_Text_K, ep_wallShade_Tint_K, \
        footprint_area_m2, vcwg_hConv_w_m2_per_K, \
        get_ep_results_inited_handle, overwrite_ep_weather_inited_handle, called_vcwg_bool, ep_last_call_time_seconds, \
        epwFileName, start_time, TopForcingFileName, VCWGParamFileName , \
        vcwg_canTemp_K_list, vcwg_canSpecHum_Ratio_list, vcwg_canPress_Pa_list, \
        EP_nFloor, EP_floor_energy_lst, EP_wall_temperatures_K_dict,\
        save_canyon_odb_c,save_canyon_rh_percent,save_floor_odb_c,save_floor_owb_c
    save_canyon_odb_c = None
    save_canyon_rh_percent = None
    save_floor_odb_c = None
    save_floor_owb_c = None

    epwFileName = _epwFileName
    start_time = _start_time
    TopForcingFileName = _TopForcingFileName
    VCWGParamFileName = _VCWGParamFileName

    get_ep_results_inited_handle = False
    overwrite_ep_weather_inited_handle = False
    called_vcwg_bool = False
    ep_last_call_time_seconds = 0

    project_path = os.path.dirname(os.path.abspath(__file__))
    bld_type = _idfFileName[0:-4]
    print(f'bld_type = {bld_type}')

    experiments_theme = _experiments_theme
    save_path_clean = False

    data_saving_path = os.path.join(project_path, 'A_saved_Cases',
                                    experiments_theme,f'{bld_type}.csv')
    ep_trivial_path = os.path.join(project_path, 'A_saved_Cases',
                                   experiments_theme, f"{bld_type}_ep_trivial_outputs")
    sys.path.insert(0, 'C:/EnergyPlusV22-1-0')
    sys.path.insert(0, '/usr/local/EnergyPlus-22-1-0/'),
    from pyenergyplus.api import EnergyPlusAPI
    ep_api = EnergyPlusAPI()
    psychrometric = None
    sem0 = threading.Semaphore(1)
    sem1 = threading.Semaphore(0)
    sem2 = threading.Semaphore(0)
    sem3 = threading.Semaphore(0)

    vcwg_needed_time_idx_in_seconds = 0
    vcwg_canTemp_K = 300
    vcwg_canSpecHum_Ratio = 0
    vcwg_canPress_Pa = 0
    vcwg_hConv_w_m2_per_K = 10
    ep_sensWaste_w_m2_per_footprint_area = 0
    ep_floor_Text_K = 300
    ep_floor_Tint_K = 300
    ep_roof_Text_K = 300
    ep_roof_Tint_K = 300
    ep_wallSun_Text_K = 300
    ep_wallSun_Tint_K = 300
    ep_wallShade_Text_K = 300
    ep_wallShade_Tint_K = 300

    if 'MedOffice' in bld_type:
        EP_nFloor = 3
        footprint_area_m2 = 53628 * 0.09290304 / 3
    elif "20Stories" in bld_type:
        EP_nFloor = 20
        footprint_area_m2 = 31 * 15
    elif 'SimplifiedHighBld' in bld_type:
        EP_nFloor = 3
        footprint_area_m2 = 31 * 15
    else:
        raise ValueError(f"bld_type = {bld_type} is not supported yet")

    EP_floor_energy_lst = []
    EP_wall_temperatures_K_dict = {}
    EP_floor_energy_lst = [0.0] * EP_nFloor
    EP_wall_temperatures_K_dict['south'] = [300] * EP_nFloor
    EP_wall_temperatures_K_dict['north'] = [300] * EP_nFloor
    EP_wall_temperatures_K_dict['east'] = [300] * EP_nFloor
    EP_wall_temperatures_K_dict['west'] = [300] * EP_nFloor

    vcwg_canTemp_K_list = [ 300 for i in range(EP_nFloor)]
    vcwg_canSpecHum_Ratio_list = [ 0 for i in range(EP_nFloor)]
    vcwg_canPress_Pa_list = [ 0 for i in range(EP_nFloor)]


def BEMCalc_Element(BEM, it, simTime, VerticalProfUrban, Geometry_m, MeteoData,
                    FractionsRoof):
    global ep_sensWaste_w_m2_per_footprint_area, save_path_clean, vcwg_needed_time_idx_in_seconds, \
        vcwg_canTemp_K_list, vcwg_canSpecHum_Ratio_list, vcwg_canPress_Pa_list, \
        vcwg_canTemp_K, vcwg_canSpecHum_Ratio, vcwg_canPress_Pa, sem0, sem1, sem2, sem3

    sem0.acquire()
    vcwg_needed_time_idx_in_seconds = (it + 1) * simTime.dt
    canTempProf_cur =  VerticalProfUrban.th[0:Geometry_m.nz_u]
    canSpecHumProf_cur = VerticalProfUrban.qn[0:Geometry_m.nz_u]
    canPressProf_cur = VerticalProfUrban.presProf[0:Geometry_m.nz_u]
    vcwg_canTemp_K = numpy.mean(canTempProf_cur)
    vcwg_canSpecHum_Ratio = numpy.mean(canSpecHumProf_cur)
    vcwg_canPress_Pa = numpy.mean(canPressProf_cur)
    '''
    Instead vcwg_canTemp_K (use one scalar value to represent all grid points within the canopy, Geometry_m.nz_u)
    To split the canopy into EP_nFloor layers:
    The first layer is the first floor,..., the last layer is for the highest floor    
    For 20Stories, each floor has one outdoor air node.
    For SimplifiedHighBld, the first floor has one outdoor air node, the 2-19th floors have same outdoor air node,
     the 20th floor has one outdoor air node.
    '''
    for i in range(EP_nFloor):
        if '20Stories' in bld_type or 'Detailed_MedOffice' in bld_type:
            # Calculate the number of grid points per floor
            nbr_grid_points_per_floor = int(Geometry_m.nz_u / EP_nFloor)
            # Calculate the starting and ending indices for the current floor
            startIndex = i * nbr_grid_points_per_floor
            endIndex = (i + 1) * nbr_grid_points_per_floor
            # Calculate the mean of the canopy temperature for the current floor
            # by extracting the corresponding range of indices
            vcwg_canTemp_K_list[i] = numpy.mean(canTempProf_cur[startIndex:endIndex])
            vcwg_canSpecHum_Ratio_list[i] = numpy.mean(canSpecHumProf_cur[startIndex:endIndex])
            vcwg_canPress_Pa_list[i] = numpy.mean(canPressProf_cur[startIndex:endIndex])
        elif 'SimplifiedHighBld' in bld_type:
            # index 0: is mean of floor 1, representative air height is around 0 -2 m
            # index 1: is mean of floor 2-19, representative air height is around 27-29 m
            # index 2: is mean of floor 20, representative air height is around 57-59 m
            floor_range_dict = {0: [0, 2], 1: [27, 29], 2: [57, 59]}
            vcwg_canTemp_K_list[i] = numpy.mean(
                canTempProf_cur[floor_range_dict[i][0]:floor_range_dict[i][1]])
            vcwg_canSpecHum_Ratio_list[i] = numpy.mean(
                canSpecHumProf_cur[floor_range_dict[i][0]:floor_range_dict[i][1]])
            vcwg_canPress_Pa_list[i] = numpy.mean(
                canPressProf_cur[floor_range_dict[i][0]:floor_range_dict[i][1]])
    sem1.release()

    sem3.acquire()
    BEM_Building = BEM.building
    if 'WithoutCooling' in bld_type:
        BEM_Building.sensWaste = 0
    else:
        BEM_Building.sensWaste = ep_sensWaste_w_m2_per_footprint_area
    ep_sensWaste_w_m2_per_footprint_area = 0

    BEM_Building.ElecTotal = 0
    BEM.mass.Text = ep_floor_Text_K
    BEM.mass.Tint = ep_floor_Tint_K
    BEM.wallSun.Text = ep_wallSun_Text_K
    BEM.wallSun.Tint = ep_wallSun_Tint_K
    BEM.wallShade.Text = ep_wallShade_Text_K
    BEM.wallShade.Tint = ep_wallShade_Tint_K
    if FractionsRoof.fimp > 0:
        BEM.roofImp.Text = ep_roof_Text_K
        BEM.roofImp.Tint = ep_roof_Tint_K
    if FractionsRoof.fveg > 0:
        BEM.roofVeg.Text = ep_roof_Text_K
        BEM.roofVeg.Tint = ep_roof_Tint_K
    # dummy values overriding
    BEM_Building.sensCoolDemand = 0
    BEM_Building.sensHeatDemand = 0
    BEM_Building.dehumDemand = 0
    BEM_Building.Qhvac = 0
    BEM_Building.coolConsump = 0
    BEM_Building.heatConsump = 0
    BEM_Building.QWater = 0.5
    BEM_Building.QGas = 0.5
    BEM_Building.Qheat = 0.5
    BEM_Building.GasTotal = 0.5
    # wall load per unit building footprint area [W m^-2]
    BEM_Building.QWall = 0.5
    # other surfaces load per unit building footprint area [W m^-2]
    BEM_Building.QMass = 0.5
    # window load due to temperature difference per unit building footprint area [W m^-2]
    BEM_Building.QWindow = 0.5
    # ceiling load per unit building footprint area [W m^-2]
    BEM_Building.QCeil = 0.5
    # infiltration load per unit building footprint area [W m^-2]
    BEM_Building.QInfil = 0.5
    # ventilation load per unit building footprint area [W m^-2]
    BEM_Building.QVen = 0.5
    BEM_Building.QWindowSolar = 0.5
    BEM_Building.elecDomesticDemand = 0.5
    BEM_Building.sensWaterHeatDemand = 0.5
    BEM_Building.sensWasteCoolHeatDehum = 0.5
    BEM_Building.indoorRhum = 0.6
    BEM_Building.fluxSolar = 0.5
    BEM_Building.fluxWindow = 0.5
    BEM_Building.fluxInterior = 0.5
    BEM_Building.fluxInfil = 0.5
    BEM_Building.fluxVent = 0.5
    BEM_Building.fluxWall = 0
    BEM_Building.fluxRoof = 0
    BEM_Building.fluxMass = 0

    if os.path.exists(data_saving_path) and not save_path_clean:
        os.remove(data_saving_path)
        save_path_clean = True
    vcwg_needed_time_idx_in_seconds = it * simTime.dt
    cur_datetime = datetime.datetime.strptime(start_time,
                                              '%Y-%m-%d %H:%M:%S') + \
                   datetime.timedelta(seconds=vcwg_needed_time_idx_in_seconds)
    print('current time: ', cur_datetime)
    wallSun_K = BEM.wallSun.Text
    wallShade_K = BEM.wallShade.Text
    roof_K = (FractionsRoof.fimp * BEM.roofImp.Text + FractionsRoof.fveg * BEM.roofVeg.Text)
    if not os.path.exists(data_saving_path):
        os.makedirs(os.path.dirname(data_saving_path), exist_ok=True)
        with open(data_saving_path, 'a') as f1:
            # prepare the header string for different sensors
            header_str = 'cur_datetime,canTemp,sensWaste,wallSun_K,wallShade_K,roof_K,' \
                         'MeteoData.Tatm,MeteoData.Pre,'
            for idx in range(len(EP_floor_energy_lst)):
                header_str += f'EP_floor_energy_J_[{idx}],'
            header_str += 'save_canyon_odb_c, save_canyon_rh_percent,'
            for flr in range(len(vcwg_canTemp_K_list)):
                header_str += f'save_floor_[{flr+1}]_odb_c,'
            for flr in range(len(vcwg_canTemp_K_list)):
                header_str += f'save_floor_[{flr+1}]_owb_c,'
            header_str += '\n'
            f1.write(header_str)
        # write the data
    with open(data_saving_path, 'a') as f1:
        fmt1 = "%s," * 1 % (cur_datetime) + \
               "%.3f," * 7 % (vcwg_canTemp_K, BEM_Building.sensWaste,
                              wallSun_K, wallShade_K, roof_K, MeteoData.Tatm, MeteoData.Pre) + \
               "%.3f," * len(EP_floor_energy_lst) % tuple(EP_floor_energy_lst) + \
                "%.3f," * 2 % (save_canyon_odb_c, save_canyon_rh_percent) + \
                "%.3f," * len(save_floor_odb_c) % tuple(save_floor_odb_c) + \
                "%.3f," * len(save_floor_owb_c) % tuple(save_floor_owb_c) + '\n'
        f1.write(fmt1)
    sem0.release()

    return BEM