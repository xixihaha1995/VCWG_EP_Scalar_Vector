import configparser, datetime, threading, sys, os,numpy

def ini_all(_experiments_theme,_idfFileName,_epwFileName,_start_time,
            _TopForcingFileName,_VCWGParamFileName):
    global config, save_path_clean,ep_trivial_path, data_saving_path, bld_type,\
        ep_api, psychrometric,\
        sem0, sem1, sem2, sem3, \
        vcwg_needed_time_idx_in_seconds, \
        vcwg_canTemp_K, vcwg_canSpecHum_Ratio, vcwg_canPress_Pa, ep_sensWaste_w_m2_per_footprint_area, \
        ep_floor_Text_K, ep_floor_Tint_K, ep_roof_Text_K, ep_roof_Tint_K, \
        ep_wallSun_Text_K, ep_wallSun_Tint_K, ep_wallShade_Text_K, ep_wallShade_Tint_K,\
        footprint_area_m2, vcwg_hConv_w_m2_per_K, \
        get_ep_results_inited_handle, overwrite_ep_weather_inited_handle, called_vcwg_bool, ep_last_call_time_seconds, \
        epwFileName, start_time,TopForcingFileName, VCWGParamFileName

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
        footprint_area_m2 = 53628 * 0.09290304 / 3
        footprint_area_m2 = 1660.73
    elif "MidRiseApartment" in bld_type:
        #46.3273m*16.9155m*12.1913m
        footprint_area_m2 = 33740 * 0.09290304 / 4
        footprint_area_m2 = 46.3273 * 16.9155
    else:
        raise ValueError(f"bld_type = {bld_type} is not supported yet")

def BEMCalc_Element(BEM, it, simTime, VerticalProfUrban, Geometry_m,MeteoData,
                    FractionsRoof):
    global ep_sensWaste_w_m2_per_footprint_area,save_path_clean,vcwg_needed_time_idx_in_seconds, \
        vcwg_canTemp_K, vcwg_canSpecHum_Ratio, vcwg_canPress_Pa, sem0, sem1, sem2, sem3

    sem0.acquire()
    vcwg_needed_time_idx_in_seconds = (it + 1) * simTime.dt
    vcwg_canTemp_K = numpy.mean(VerticalProfUrban.th[0:Geometry_m.nz_u])
    vcwg_canSpecHum_Ratio = numpy.mean(VerticalProfUrban.qn[0:Geometry_m.nz_u])
    vcwg_canPress_Pa = numpy.mean(VerticalProfUrban.presProf[0:Geometry_m.nz_u])
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
            header_str += '\n'
            f1.write(header_str)
        # write the data
    with open(data_saving_path, 'a') as f1:
        fmt1 = "%s," * 1 % (cur_datetime) + \
               "%.3f," * 7 % (vcwg_canTemp_K,BEM_Building.sensWaste,
                              wallSun_K,wallShade_K,roof_K,MeteoData.Tatm, MeteoData.Pre) + '\n'
        f1.write(fmt1)
    sem0.release()

    return BEM