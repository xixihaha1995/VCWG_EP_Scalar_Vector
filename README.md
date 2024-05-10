# Citation

We'd appreciate if you cite this [B&E journal paper](https://www.sciencedirect.com/science/article/pii/S0360132323010867) using citation below:

```bibtex
@article{RN13245,
   author = {Wang, Liping and Wu, Lichen and Norford, Leslie Keith and Aliabadi, Amir A. and Lee, Edwin},
   title = {The interactive indoor-outdoor building energy modeling for enhancing the predictions of urban microclimates and building energy demands},
   journal = {Building and Environment},
   volume = {248},
   pages = {111059},
   ISSN = {0360-1323},
   DOI = {https://doi.org/10.1016/j.buildenv.2023.111059},
   url = {https://www.sciencedirect.com/science/article/pii/S0360132323010867},
   year = {2024},
   type = {Journal Article}
}
```

# Procedures to replicate the research paper results

1. The original VCWGv2.0.0 is available at [VCWGv2.0.0](https://github.com/AmirAAliabadi/VCWGv2.0.0)
2. Install [EnergyPlus](https://github.com/NREL/EnergyPlus/releases/tag/v22.1.0) at `sys.path.insert(0, 'C:/EnergyPlusV22-1-0')` or `sys.path.insert(0, '/usr/local/EnergyPlus-22-1-0/')`
3. Two-way coupling is available at [High Rise Office Two-way](https://github.com/xixihaha1995/VCWG_EP_Scalar_Vector/tree/vector), [Med Office Two-way](https://github.com/xixihaha1995/VCWG_EP_Scalar_Vector/tree/scalar). (You may find some files from original [VCWGv2.0.0](https://github.com/AmirAAliabadi/VCWGv2.0.0) have been adopted to work with EnergyPlus, such as this [line](https://github.com/xixihaha1995/VCWG_EP_Scalar_Vector/blob/82d00061e571996c50c4165a9540f391cd0b5c73/VCWG_Hydrology.py#L620); important files: `_0_main_epTimestepHandlers.py` and `_1_parent_coordination.py`)
4. One-way coupling is available at [High Rise Office One-way](https://github.com/xixihaha1995/VCWG_EP_Scalar_Vector/tree/vector-one-way), [Med Office One-way](https://github.com/xixihaha1995/VCWG_EP_Scalar_Vector/tree/scalar-one-way). (You may find some files from original [VCWGv2.0.0](https://github.com/AmirAAliabadi/VCWGv2.0.0) have been adopted. **Remember** one-way coupling urban weather calculation is directly modified from two-way couplings, so they are closer to two-way coupling, not the origianl VCWGv2.0.0, for example this [line](https://github.com/xixihaha1995/VCWG_EP_Scalar_Vector/blob/2031984d05eaae052f6d8b45d214c9e5a380e63f/VCWG_Hydrology.py#L622). This is because two-way couplings code development was gotten more efforts and developed earlier than one-way coupling, especially when conduct the sensitivity analysis, multiple cases running together for time efficiency purposes using multiprocessing.)
5. Validation: All the processed rural and urban weather measurements are available at this [repo-branch](https://github.com/xixihaha1995/urban_climate_and_who/tree/why_improvements_on_Bypass/A_prepost_processing/_measurements), for original datasets [BUBBLE](https://ibis.geog.ubc.ca/~achristn/research/BUBBLE/data/BUBBLE_AT_IOP.txt,), [CAPITOUL](https://www.aeris-data.fr/en/catalogue-en/#masthead),[VANCUVER](https://ibis.geog.ubc.ca/~achristn/infrastructure/sunset.html)
6. The entire paper code and dataset is **fully** hosted on repos (ranked by time descending order) (In case you want to find some files/settings, you need to explore among all the **branches** of the following repos):
    - [VCWG-EP-Scalar-Vector](https://github.com/xixihaha1995/VCWG_EP_Scalar_Vector)
    - [VCWG-EP-Experiments](https://github.com/xixihaha1995/VCWG_EP_Experiments)
    - [Urban climate and Who](https://github.com/xixihaha1995/urban_climate_and_who)
7. You might find this repo insightful about the rural and weather files, UWG/VCWG settings at [UWG-Matlab](https://github.com/hansukyang/UWG_Matlab)
8. Please email me to `lwu4@uwyo.edu` if you have any questions or need further assistance.
