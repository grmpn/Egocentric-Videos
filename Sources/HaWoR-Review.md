[https://hawor-project.github.io/](https://hawor-project.github.io/)

Understand the full paper pipeline “in depth” → Agent Plan Mode → Implement blocks one at a time, fully understanding every choice that has been made, **not** the low-level code.

Focus on the novel additions of the paper, **not** on recreating established CV algorithms like SLAM. 

The overall goal of the project is to be able to extract world-frame hand trajectories from RGB only input. I see this as being 3 systems put together to get the final extraction: Camera-frame hand tracking, 3D SLAM trajectory tracking, and the hand motion infiller. These are combined to extract the world-frame hand trajectory. 

Issues I may run into while implementing: exact “meaning” of the 6D rotation matrices output by the model (local, global, camera, etc.). Exact loss functions. Transforming the NN outputs to the 3d joints, 2d joints, etc. Using the NN outputs to construct the MANO hand model. Exactly how to do the conversions from NN output and still allow for gradients to flow. 

**Potential major oversight/flaw? IGNORE THIS; INTERPOLATOR IS A NO-OP DUE TO HOW THE ACTUAL CODE IS STRUCTURED (leftover code from the something to do with evaluation against GT examples–but why do they need it for GT; idk doesnt matter)**

- Before running the hand estimator model, SLAM, or camera infiller, HaWoR uses the off-the shelf hand detector on every frame of a trajectory  
- If less than two frames with hands are confidently detected, they will not even run the pipeline on that trajectory   
- **However, if any two frames with hands are confidently detected, they will interpolate bounding boxes for all of the undetected frames between the detected frames, no matter the size of the gap between the detected frames.**  
- **ADDITIONALLY,** these interpolated bounding boxes are treated as **valid frames, even if the interpolation is wrong and there is NO HAND in the bounding box**, so they will not be modified by the camera infiller  
- This means that, if a trajectory has two or more detected hand frames, the only way there can be “missing” frames that the camera infiller modifies, is if they are before the first detected frame, or after the last detected frame.  
  - What is even the point of the camera infiller then?  
- **Verify if this is actually a problem, or if everything somehow works out due to attention/context from other frames, etc. Or if there actually is some way this is addressed**  
- I feel like it would still be good to store what frames were interpolated…  
- If hands go off camera, you can probably assume they are mostly stationary, since they shouldn’t be doing anything important off camera?  
- **Need to think about this more**

**Confidence estimate ideas**

- Base the confidence off the gap between valid and missing frames  
  - Middle frame of a gap \= less confident than those right before and after valid frames  
  - Longer frame gaps should have much less confidence (ex. Middle of a 100 frame gap should have almost 0 confidence, while the middle of a 3 frame gap could still have a high confidence)  
- 2D reprojection consistency confidence, may be too expensive  
- Acceleration consistency   
- Easiest \= based off hand detection score from the model that generates the bounding box

**Adding a confidence estimate to model output**

- Look into the Gaussian uncertainty loss  
- Would motion infilling uncertainty be enough?  
  - I think it might be, since there potential errors from metric SLAM, hand estimation just have to be accepted as parts of the pipeline  
- There is no false positive detection for the hand bounding box though. This is basically the limitation the authors mention → reliance on the off-the-shelf hand detection can lead to errors propagating from hand detection → hand estimation → SLAM → overall trajectory being off.  
- This doesn’t change the fact that the hand motion infiller can still operate on large gaps. So, it might be valid to introduce that confidence score to the hand motion infiller.

**HOW TO ALIGN THE XYZ AXIS ORIENTATIONS BETWEEN TRAJECTORIES?**

- When they test results against benchmarks, they still have to align orientation and translation, even though scale should already be correct.   
- Is the solution that is usually used converting into some hand space coordinate frame, kind of like the canonical frame from HaWoR – this might be easier than trying to convert to some sort of shared world frame.   
- Then, we can convert the canonical frame to the frame used by the robot controller at inference – the model still predicts the canonical frame.

**Need to think about when to throw away a clip (specifically related to hands not being visible). After 4 seconds of no hands detected? 6 seconds? Other criteria?**

Camera-Frame 3D Hand Tracking

Get a concrete answer to why the wrist position (depth) is able to be metrically grounded. I understand the hand points, since they are relative to the wrist position and based on the MANO model.  
***Hand Detection***

- The camera-frame hand tracking network does not take raw RGB as an input  
- It needs a **cropped frame of the hand**  
- To get the cropped frame, we first run an off-the-shelf hand detector and tracker that will give a **bounding box for the hand**  
- We also need a **handedness estimate**; the network only works with right hand inputs, so left hand images/videos will need to be mirrored before being input to the network

***Direct Learned-Layer Inputs***

- **RGB hand crop** → Directly enters ViT  
  - *BxTx3x256x256*  
  - The crop is derived by scaling the hand bounding box extraction by 1.2x   
  - Scaling gives more image context around the hand  
  - Constructed from center and scale

- **3D bounding box descriptor** → used in IAM and PAM layers  
  - *BxTx3*  
  - Constructed from center, scale, img\_focal, and img\_center  
  - **qx, qy, qs**  
    - **qx** \= horizontal displacement from image center, normalized by focal length  
    - **qy** \= vertical displacement from image center, normalized by focal length  
    - **qs** \= apparent size of the hand bounding box, relative to focal length. Gives some idea of depth. Larger apparent hand \= hand closer to camera, usually.  
  - The point of the bounding box descriptor is to give the model information about where the normalized crop came from and how large it was originally.

***Inputs Used for Geometrical Roles/Deriving Further Outputs from Raw NN Outputs***

- center: **Bounding Box Center**   
  - *BxTx**2***  
  - The x and y pixel coordinates of the center of the bounding box, relative to the original, uncropped image origin

- scale: **Bounding Box Scale**  
  - *BxT*  
  - Scale parameter that represents the size of the bounding box  
  - 1/200 of the square bounding box side length in pixels

- img\_focal: **Focal Length**  
  - *BxT*  
  - Focal length of the camera in pixels  
  - If none is provided, default is 600 pixels

- img\_center: **Original Image Center**  
  - *BxTx**2***  
  - x and y pixel coordinates of the center of the original, uncropped image

***Direct NN Outputs***

- **Hand Pose**  
  - *Shape:* BxTx**16x6**  
  - 1 global wrist orientation, 15 hand joint rotations (axis-angle)  
  - The neural network uses a 6D representation of the rotations  
- **MANO Hand Parameters**  
  - *Shape:* BxTx**10**  
  - The mano parameters define hand proportions, width, **finger length,** shape, etc.  
- pred\_cam: **Camera Parameters**  
  - *Shape:* BxTx**3**  
  - See HaMeR camera parameters  
  - The camera parameters help to reconstruct the hand position in the 3D camera frame

***Outputs Derived from Direct NN Outputs***

- trans\_full: **Full camera-space translation**   
  - Constructed from pred\_cam, center, scale, img\_focal, and img\_center  
  - Outputs the full hand trajectory chunk in the camera frame  
  - Z \= 2f/bs; this reconstructs the hand object  Z distance from the camera. Derive the formula by hand  
  - X, Y are reconstructed using the pinhole equation with the tx and ty network outputs added on as correction factors that indicate how far the center of the hand is from the center of the cropped bounding box.  
  - **THE WHOLE THING CAN ONLY BE IN METRIC DUE TO THE MANO HAND MODEL. The predictions are grounded within the MANO hand model. It directly predicts the parameters of the MANO hand model, and then has to place that predicted hand model into the world. The trajectory of the hand, if the size of the hand is known, can only be explained through a certain world frame trajectory.**

- **3D to 2D projection**  
  - Projects the 3D hand trajectory onto the full 2D camera image using img\_focal, and img\_center  
  - Uses pinhole projection  
  - center and scale are used to convert the 2D projected trajectory into coordinates relative to the **normalized** crop  
  - Used for training loss → having it be within the normalized crop allows for patterns to be extracted more easily without having to think about differences based on the scale of the bounding box

***Architecture***  
Frozen WiLoR ViT Backbone → IAM → MANO decoder → PAM

**ViT Backbone**

- The ViT Backbone is taken from WiLoR and **frozen** during training  
- WiLoR is another hand-tracking network, so the ViT has already learned single-image hand representations  
- **Input:** BxTx3x256x256 Hand crops (256x256 → 256x192 through further horizontal crop)  
- **Batch and Time flattened:** BxTx3x256x192 → (BxT)x3x256x192  
  - The ViT essentially sees BxT independent images → This is essentially done because the ViT expects an input of shape Nx3xHxW  
- **Image tokens**  
- WiLoR ViT uses patch size of 16x16 pixels  
  - 256/16 \= 16; 192/16 \= 12 → 16x12 image tokens  
  - 16 rows, 12 columns of image tokens  
  - Overall 192 image tokens per frame  
  - Each patch is represented by a feature vector of dimension 1280 within one image token  
- **Output:** Spatial image tokens that compress the information of image patches; shape is (Bx16)x1280x16x12

**IAM: Image Attention Module**

- **Input:** ViT output → (BxT)x1280x16x12

- BBox descriptors appended → (BxT)x1283x16x12

- Rearrange Spatial location into independent temporal sequences → (Bx16x12)xTx1283

- Projection Layer → (Bx16x12)xTx512

- Temporal Positional Encoding \+ 6 transformer layers (unmasked self-attention) → (Bx16x12)xTx512  
  - In the attention, spatial tokens corresponding to patches at the same position attend to each other across time.   
  - For example, patch 1 at frame 1 attends to patch 1 at frames 2, 3, etc.

- Projection Layer → (Bx16x12)xTx1280

- Rearrange to original ViT layout → (BxT)x1280x16x12

- **Output:** Add original ViT feature residual → (BxT)x1280x16x12

**MANO Transformer Decoder** 

- **Input:** IAM output → (BxT)x1280x16x12

- Context token rearranged from the IAM output → (BxT)x192x1280

- Query Token is created → (BxT)x1x1024  
  - Starts as a (BxT)x1x1 zero token that is projected to the final dimension through a linear layer with bias and learned positional embeddings  
  - The reason for starting from the zero token is not significant

- Cross Attention between query token and keys and values from the context token  
  - Queries, keys and values are 512D  
  - Output of cross attention is projected back to 1024D and added residually to the original query token

- **Output:** Contextualized decoder token → (BxT)x1024

- Three Regression heads map the decoder token to Hand Pose \[(BxT)x**96**\], MANO hand parameters \[(BxT)x**10**\], and Camera Parameters \[(BxT)x**3**\]

**PAM: Pose Attention Module**

- The PAM allows hand poses to attend to each over time to ensure they are consistent with each other.  
  - The MANO decoder only attended across visual patch tokens of the same frame.   
  - Although these had temporal information from the IAM, the Hand poses are ultimately constructed independent of each other, so they may still be inconsistent.

- **Input:** (BxT)x96 pose prediction

- Append 3D Bounding Box Descriptor → (BxT)x99 

- Restore Temporal Axis → BxTx99

- Linear Projection, then add sinusoidal positional encodings → BxTx384

- Multi Head Self attention Across the temporal dimension (frame 1 attends to frames 2,3,4 etc.)  
  - This is within 6 transformer encoder layers that use 1024D feedforward networks

- **Output:** Project back to 96D and flatten Batch/Time → (BxT)x96

- There is no outer residual connection, so the PAM output is the final pose estimation—it is not added onto the original MANO decoder pose estimation.

***Loss Function:*** 1L3D+2L2D+3LMANO  
Important Symbols:

- *p \=* Hand Pose estimation, output by MANO decoder (*p0*), refined by PAM (*pfinal*)   
  - 𝚽 \= orientation of the wrist (relative to camera)  
  - Θ \= local axis-angle rotation matrix of the fingers   
- *c \=* Camera parameter estimation, output by MANO decoder  
- 𝛽 \= MANO shape parameter estimation, output by MANO decoder

**3D joints loss term**

- 3D joints are derived from processing the NN output  
  - MANO decoder output *p0* → PAM output *pfinal* → (*pfinal*, 𝛽) → MANO Model → 3D joints

- Basic equation: || J3D, pred-J3D,real||  
  - Minimize the absolute difference between the 3D joints constructed from NN predictions and the ground truth 3D joints  
  - L1 loss

- Full equation: j=121Xpred-Xreal+Ypred-Yreal+Ypred-Yreal

**2D projected joints loss term**

- 2D joints are derived from processing the NN output  
  - (3D joints, *c*, camera geometry) → 2D projected points  
- This loss term allows the model to be trained even from data that only has ground truth 2D labels.

- Basic equation: || J2D, pred-J2D,real||  
  - Minimize the absolute difference between the 2D joints constructed from NN predictions and the ground truth 2D joints  
  - L1 loss

- Full equation: j=121Xpred-Xreal+Ypred-Yreal

**MANO shape parameters loss term**

- MANO shape parameters, 𝛽, are directly predicted by the MANO decoder. Θ is directly predicted from the PAM

- Basic equation: pred-real2\+pred-real2+pred-real2  
  - L2 loss   
  - The phi term is not explicitly stated in the paper, but I think it is in the code.  
  - Minimize the squared absolute difference between the MANO shape parameters and hand orientations predicted by the NN and the ground truth

***Training Example***  
What ground truth values are needed?

- img  
- center  
- scale  
- img\_focal  
- img\_center  
- gt\_cam\_j2d → ground truth 2d joint positions  
- gt\_j3d\_wo\_trans → ground truth 3d joint positions  
- gt\_cam\_betas → ground truth MANO shape parameters

3D SLAM Trajectory Tracking

Explore using a DROID-W based workflow instead of DROID-SLAM. DROID-W trajectory should already be approximately metric

***High Level DROID-SLAM Architecture***   
**DROID-SLAM Inputs \+ Outputs**

- **Input**: RGB frames, camera intrinsics  
  - RGB frames are downsampled to 1/8 Scale  
  - There is no frame “chunk” that is input to the model. The model takes in frames one-by-one and uses a motion filter to decide which frames are useful keyframes for motion tracking  
  - 12 keyframes need to be accumulated to initialize the SLAM system  
  - RGB Frames are used as a direct NN input to give visual information  
  - The camera intrinsics are used for SLAM calculations that transform the output of the NN  
    - This does not mean they do not help train the NN. The loss functions likely compare these final outputs to the ground truth, so the gradient will backpropagate through the NN from the SLAM calculations

- **Final Output**: Camera trajectory as translation and quaternion orientation per frame \+ Relative scene depth

**Refinement Flow to get Final Output**

1. DROID has current estimates of camera poses and depth for a fixed and target frame  
   2. They actually use inverse-depth. Inverse depth is initialized as 1\. And the camera pose is initialized as an identity matrix.

3. Using camera intrinsics and current estimates → project where a point from the fixed frame is in the target frame  
   4. 2D Point in fixed frame → 3D point → Project that 3D point to another 2D point in the target frame

5. Both 2D points \+ RGB frames → NN → Delta position corrections to 2D point in target frame \+ confidence level  
   6. These delta positions are defined on the 1/8 Image scale used by DROID-SLAM (ex. 30x40 grid instead of 240x320 raw RGB)  
   7. The delta positions can place the new 2D position outside the grid. In this case, the prediction is heavily downweighted in Bundle Adjustment

8. Delta Corrections \+ Confidence Level → Bundle Adjustment → Inverse Dynamics → New Camera pose and depth

9. Repeat

***What is added by HaWoR?***  
**Hand Masking**

- The hands are masked by projecting the mano mesh onto the 2d frames and then rasterizing to get a mask  
- Hands are masked out from the image input, so the NN shouldn’t predict any delta corrections for those pixels  
- Even if a delta correction is produced, the confidence weights used by dense bundle adjustment are set to 0

**Scale Adjustment**

- HaWoR adds Metric3D into the pipeline to estimate the physical depth of the scene in metric coordinates  
- They use the assumption that DMetric3DDSLAM  
- They want to solve for alpha, the scale factor between the metric depth and the SLAM depth. Alpha can be used to convert the SLAM trajectory to a metric trajectory.

1. **Droid Depth \+ Metric3D depth**  
   2. This process is performed on upsampled depth maps, not the 1/8 image scale representation used for SLAM calculations  
3. **remove hand and undesired depth ranges**  
   4. Acceptable Depth range: 0.4 to 0.7 m  
5. **Median depth ratio initialization**   
- (they calculate the depth ratio per pixel and use the median value as the starting estimate for alpha)  
4. **Iterative valid-point refinement**  
   5. First they take the median of the alphas calculated from the ratio between the Metric3D depth prediction and the SLAM depth prediction of all pixel values within the constrained depth range and not including hands.  
   6. Then they calculate the metric depth from SLAM and the median alpha value.  
   7. They then calculate all alphas again, this time also removing from the calculation the pixels where the calculated metric depth from SLAM was outside of the depth range  
      1. This step basically removes pixels where SLAM and Metric3D heavily disagree with each other  
   8. This process is used to give the optimizer a good initial estimate to start from.  
   9. Potential refinement: Start with the Metric3D hard depth mask, but then compare the error between Metric3D and metric SLAM to refine the mask instead of deleting pixels where metric SLAM is outside of depth range. Also, instead of making a hard mask, potentially downweight the values that disagree instead of completely eliminating them.  
      1. This is probably not necessary due to the Geman-McClure optimization  
10. **Geman-McClure robust optimization leads to final alpha value**  
   11. Optimizes the depth residual across the valid pixels  
   12. The Geman-McClure loss is chosen to cap the effects of large outliers. Outliers might be especially common here from occlusions, reflective surfaces, moving objects, etc.  
   13. Large outliers are bad because if we have one pixel that contributes a massive loss, that will skew the overall gradient to be closer to the gradient that will optimize that pixel. This can result in the final output being skewed towards the outlier. 

   14. 2r22+r2 

   15. σ \= arbitrary scaling variable

   16.  r \= Dtrue-DSLAM 

Hand Motion Infiller \+ The Canonical Frame

Hand detection every frame. Frames where no hand is detected \= missing frames. Then, they create inputs to the hand estimation model by splitting at frames where there are gaps afterwards (ex. Detections at \[1,2,3,10,11,12\] become example \[1,2,3\] and example \[10,11,12\].

The missing frames are marked and then are fed into the hand motion infiller later as part of a larger sequence. 

***The Canonical Frame***  
Hand predictions for each frame are in the camera frame. This makes infilling across frames difficult because we have to account for hand movement and camera movement.

This problem is the motivation for introducing the canonical frame. The canonical frame sets the hands root translation (𝚪) to 0 and its wrist orientation (𝚽) to identity at the first frame (identity matrix \= no rotation).

The coordinate system is defined around the hand’s initial state. Canonical axes are rotated from the world frame so they align with **initial hand root orientation**.

Finger rotations are not modified, since they are local MANO rotations. MANO parameters are also unchanged.

**Conversion to the Canonical Frame**

- Camera frame → World Frame → Canonical Frame

Essentially, the canonical frame allows the hand infiller to learn the relative hand motion, rather than having to reason across the camera movements. 

***Architecture***  
They use LERP (linear interpolation) and SLERP (spherical linear interpolation) on the missing rotations (SLERP), translations (LERP), and MANO parameters (LERP). 

These interpolations are the starting point for the model, which then outputs corrections to these predictions.

**Input:** BxTx219 tensor representation of both hands (T \= 120 here, not 16\)

- Per Hand: 3trans,root \+ 10β \+ 6rot,root \+ 15 x 6rot,joints   
- 109D x 2 hands \= 218D \+ binary validity mask \= 219D  
  - The binary validity mask is 1 if both hands are valid at frame *t* and 0 if otherwise

Linear Projection \+ Positional Encoding → BxTx384

Multi-Head Masked Self-Attention

- Within 8 transformer encoder blocks that use 2048D feed-forward networks  
- The missing/unfilled frames are allowed to be queries, but they are masked from being keys or values

Multi-Head Self Attention

- Within 8 transformer encoder blocks that use 2048D feed-forward networks  
- The missing/unfilled frames are now allowed to be queries, keys, and values

**Output:** MLP maps transformer output → BxTx2x109 updated/infilled tensor representation of both hands

The validity mask is both used as information by the transformer, but also used to construct the attention mask during the first 8 transformer encoder blocks, guiding the network more.

***Loss Function:***  t=1T(1L+2L+3L+4L)

- L \=pred-real; Root translation loss term

- L=pred-real; Root orientation loss term

- L=pred-real; Finger orientation loss term

- L=pred-real; MANO shape parameter loss term

- The loss supervises the complete sequence, including valid frames  
  - This essentially tells the model to keep values associated with valid frames the same, while changing those associated with invalid frames