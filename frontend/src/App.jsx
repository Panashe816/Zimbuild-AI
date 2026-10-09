import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE_URL = "https://zimbuild-ai.onrender.com";
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";

/*
|--------------------------------------------------------------------------
| ZimBuild AI - Frontend
|--------------------------------------------------------------------------
|
| Residential architectural plan analysis and construction estimation.
|
| Important:
| - The interface does not expose internal pricing formulas.
| - Transport and location calculations remain backend responsibilities.
| - Roof detection/calculation is not currently supported.
|
|--------------------------------------------------------------------------
*/

const LOCATION_OPTIONS = [
  {
    value: "city_town",
    label: "City / Big town",
    description: "Major urban centre",
  },
  {
    value: "growth_point",
    label: "Small town / Growth point",
    description: "Small town or growth point",
  },
  {
    value: "rural_farm",
    label: "Rural area / Farm",
    description: "Rural or farm location",
  },
];

const DEFAULTS = {
  wallHeight: "2.4",
  foundationWidth: "0.2",
  foundationDepth: "0.3",
  slabThickness: "0.15",
  hardcoreDepth: "0.15",
  wallThickness: "0.15",
  wastagePercentage: "5",
  reinforcementRuns: "3",
  brickForceInterval: "4",
  meshAllowance: "10",
  scaleRatio: "100",
  locationProfile: "growth_point",
};

function App() {
  const [step, setStep] = useState(1);

  // -----------------------------------------------------------------------
  // Google authentication
  // -----------------------------------------------------------------------

  const [authUser, setAuthUser] = useState(() => {
    try {
      const savedUser = localStorage.getItem("zimbuild_auth_user");
      return savedUser ? JSON.parse(savedUser) : null;
    } catch {
      return null;
    }
  });

  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");
  const googleButtonRef = useRef(null);

  // -----------------------------------------------------------------------
  // Project information
  // -----------------------------------------------------------------------

  const [projectName, setProjectName] = useState("");
  const [location, setLocation] = useState("");
  const [locationProfile, setLocationProfile] = useState(
    DEFAULTS.locationProfile
  );

  // -----------------------------------------------------------------------
  // Architectural plan
  // -----------------------------------------------------------------------

  const [planFile, setPlanFile] = useState(null);
  const [storedFilename, setStoredFilename] = useState("");
  const [processedFilename, setProcessedFilename] = useState("");

  // -----------------------------------------------------------------------
  // Construction parameters
  // -----------------------------------------------------------------------

  const [wallHeight, setWallHeight] = useState(DEFAULTS.wallHeight);
  const [foundationWidth, setFoundationWidth] = useState(
    DEFAULTS.foundationWidth
  );
  const [foundationDepth, setFoundationDepth] = useState(
    DEFAULTS.foundationDepth
  );
  const [slabThickness, setSlabThickness] = useState(
    DEFAULTS.slabThickness
  );
  const [hardcoreDepth, setHardcoreDepth] = useState(
    DEFAULTS.hardcoreDepth
  );
  const [wallThickness, setWallThickness] = useState(
    DEFAULTS.wallThickness
  );
  const [wastagePercentage, setWastagePercentage] = useState(
    DEFAULTS.wastagePercentage
  );

  // -----------------------------------------------------------------------
  // Reinforcement / masonry specifications
  // -----------------------------------------------------------------------

  const [reinforcementRuns, setReinforcementRuns] = useState(
    DEFAULTS.reinforcementRuns
  );

  const [brickForceInterval, setBrickForceInterval] = useState(
    DEFAULTS.brickForceInterval
  );

  const [meshRequired, setMeshRequired] = useState(true);

  const [meshAllowance, setMeshAllowance] = useState(
    DEFAULTS.meshAllowance
  );

  // -----------------------------------------------------------------------
  // Scale
  // -----------------------------------------------------------------------

  const [scaleRatio, setScaleRatio] = useState(DEFAULTS.scaleRatio);

  // -----------------------------------------------------------------------
  // UI state
  // -----------------------------------------------------------------------

  const [isUploading, setIsUploading] = useState(false);
  const [isEstimating, setIsEstimating] = useState(false);

  const [mapAnalysisState, setMapAnalysisState] = useState("idle");

  const [errorMessage, setErrorMessage] = useState("");

  const [result, setResult] = useState(null);

  // Stores the successful Vision analysis shown before construction inputs.
  const [visionAnalysis, setVisionAnalysis] = useState(null);

  // User-editable values for the detected visualisation.
  // These are initialised from the Vision result and are sent to the
  // backend when the estimate is generated.
  const [visionEdits, setVisionEdits] = useState({
    floorArea: "",
    walls: "",
    rooms: "",
    doors: "",
    windows: "",
    wallLength: "",
  });

  const [selectedLocation, setSelectedLocation] =
    useState(LOCATION_OPTIONS[1]);

  // -----------------------------------------------------------------------
  // Load Google Identity Services
  // -----------------------------------------------------------------------

  useEffect(() => {
    if (authUser || !GOOGLE_CLIENT_ID) {
      return;
    }

    const existingScript = document.querySelector(
      'script[src="https://accounts.google.com/gsi/client"]'
    );

    const initialiseGoogleSignIn = () => {
      if (!window.google?.accounts?.id || !googleButtonRef.current) {
        return;
      }

      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleCredential,
      });

      googleButtonRef.current.innerHTML = "";

      window.google.accounts.id.renderButton(
        googleButtonRef.current,
        {
          theme: "outline",
          size: "large",
          text: "continue_with",
          shape: "rectangular",
          width: 320,
          logo_alignment: "left",
        }
      );
    };

    if (existingScript) {
      if (window.google?.accounts?.id) {
        initialiseGoogleSignIn();
      } else {
        existingScript.addEventListener(
          "load",
          initialiseGoogleSignIn,
          { once: true }
        );
      }

      return () => {
        existingScript.removeEventListener(
          "load",
          initialiseGoogleSignIn
        );
      };
    }

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = initialiseGoogleSignIn;
    document.head.appendChild(script);

    return () => {
      script.onload = null;
    };
  }, [authUser]);

  // -----------------------------------------------------------------------
  // Verify Google credential with the backend
  // -----------------------------------------------------------------------

  const handleGoogleCredential = async (response) => {
    if (!response?.credential) {
      setAuthError("Google sign-in did not return a valid credential.");
      return;
    }

    setAuthLoading(true);
    setAuthError("");

    try {
      const authResponse = await fetch(
        `${API_BASE_URL}/auth/google`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            credential: response.credential,
          }),
        }
      );

      const data = await authResponse.json();

      if (!authResponse.ok) {
        throw new Error(
          data.detail || "Google sign-in could not be completed."
        );
      }

      if (!data.user) {
        throw new Error(
          "The authentication server did not return a user profile."
        );
      }

      localStorage.setItem(
        "zimbuild_auth_user",
        JSON.stringify(data.user)
      );

      if (data.token) {
        localStorage.setItem(
          "zimbuild_auth_token",
          data.token
        );
      }

      setAuthUser(data.user);
    } catch (error) {
      setAuthError(
        error.message ||
          "Unable to sign in with Google. Please try again."
      );
    } finally {
      setAuthLoading(false);
    }
  };

  const handleSignOut = () => {
    localStorage.removeItem("zimbuild_auth_user");
    localStorage.removeItem("zimbuild_auth_token");
    setAuthUser(null);
    setAuthError("");
  };

  // -----------------------------------------------------------------------
  // Update selected location
  // -----------------------------------------------------------------------

  useEffect(() => {
    const option = LOCATION_OPTIONS.find(
      (item) => item.value === locationProfile
    );

    if (option) {
      setSelectedLocation(option);
    }
  }, [locationProfile]);

  // -----------------------------------------------------------------------
  // Clean image preview URL
  // -----------------------------------------------------------------------

  useEffect(() => {
    return () => {
      if (planFile?.previewUrl) {
        URL.revokeObjectURL(planFile.previewUrl);
      }
    };
  }, [planFile]);

  // -----------------------------------------------------------------------
  // File selection
  // -----------------------------------------------------------------------

  const handleFileChange = (event) => {
    const file = event.target.files?.[0] ?? null;

    if (!file) {
      return;
    }

    setErrorMessage("");

    const previewUrl = URL.createObjectURL(file);

    setPlanFile({
      file,
      previewUrl,
    });

    setMapAnalysisState("idle");
    setProcessedFilename("");
    setStoredFilename("");
    setVisionAnalysis(null);
    setVisionEdits({
      floorArea: "",
      walls: "",
      rooms: "",
      doors: "",
      windows: "",
      wallLength: "",
    });
  };

  // -----------------------------------------------------------------------
  // Upload and prepare plan
  // -----------------------------------------------------------------------

  const uploadAndPreparePlan = async () => {
    if (!planFile?.file) {
      throw new Error("Please select an architectural plan.");
    }

    const formData = new FormData();
    formData.append("file", planFile.file);

    const uploadResponse = await fetch(
      `${API_BASE_URL}/plans/upload`,
      {
        method: "POST",
        body: formData,
      }
    );

    const uploadData = await uploadResponse.json();

    if (!uploadResponse.ok) {
      throw new Error(
        uploadData.detail || "Plan upload failed."
      );
    }

    const uploadedFilename =
      uploadData.stored_filename ||
      uploadData.filename ||
      uploadData.file?.stored_filename;

    if (!uploadedFilename) {
      throw new Error(
        "The backend did not return a stored filename."
      );
    }

    setStoredFilename(uploadedFilename);

    const preprocessResponse = await fetch(
      `${API_BASE_URL}/plans/preprocess/${encodeURIComponent(
        uploadedFilename
      )}`,
      {
        method: "POST",
      }
    );

    const preprocessData = await preprocessResponse.json();

    if (!preprocessResponse.ok) {
      throw new Error(
        preprocessData.detail ||
          "The architectural plan could not be prepared."
      );
    }

    const preparedFilename =
      preprocessData.processed_filename ||
      preprocessData.filename ||
      preprocessData.processed?.processed_filename;

    if (!preparedFilename) {
      throw new Error(
        "The backend did not return a processed plan."
      );
    }

    setProcessedFilename(preparedFilename);

    return preparedFilename;
  };

  // -----------------------------------------------------------------------
  // Run the actual NEW Vision analysis
  // -----------------------------------------------------------------------

  const analysePreparedPlan = async (preparedFilename) => {
    const query = new URLSearchParams({
      scale_ratio: String(scaleRatio),
      wall_height_m: String(wallHeight),
      wall_thickness_m: String(wallThickness),
      wastage_percentage: String(wastagePercentage),
      threshold: "0.5",
    });

    const response = await fetch(
      `${API_BASE_URL}/estimation/calculate/${encodeURIComponent(
        preparedFilename
      )}?${query.toString()}`,
      {
        method: "POST",
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.detail || "AI visualisation failed."
      );
    }

    if (!data.phase8) {
      throw new Error(
        "The AI visualiser completed but returned no analysis result."
      );
    }

    setVisionAnalysis(data.phase8);

    const analysed = data.phase8 || {};
    const analysedWalls = analysed.walls || {};
    const analysedRooms = analysed.rooms || {};
    const analysedDoors = analysed.doors || {};
    const analysedWindows = analysed.windows || {};
    const analysedFloor = analysed.floor || {};

    setVisionEdits({
      floorArea: String(
        analysedFloor.recommended_floor_area_m2 ??
          analysedFloor.printed_total_floor_area_m2 ??
          0
      ),
      walls: String(analysedWalls.count ?? 0),
      rooms: String(analysedRooms.count ?? 0),
      doors: String(analysedDoors.count ?? 0),
      windows: String(analysedWindows.count ?? 0),
      wallLength: String(analysedWalls.total_wall_length_m ?? 0),
    });

    return data;
  };

  // -----------------------------------------------------------------------
  // Step 1 submit - upload, preprocess, then actually analyse with Vision
  // -----------------------------------------------------------------------

  const handleProjectSubmit = async (event) => {
    event.preventDefault();

    setErrorMessage("");

    if (!projectName.trim()) {
      setErrorMessage("Please enter a project name.");
      return;
    }

    if (!location.trim()) {
      setErrorMessage("Please enter the project location.");
      return;
    }

    if (!planFile?.file) {
      setErrorMessage("Please upload an architectural plan.");
      return;
    }

    setIsUploading(true);
    setMapAnalysisState("analysing");
    setVisionAnalysis(null);

    try {
      const preparedFilename = await uploadAndPreparePlan();
      await analysePreparedPlan(preparedFilename);

      setMapAnalysisState("analysed");
      setStep(2);
    } catch (error) {
      setMapAnalysisState("idle");
      setVisionAnalysis(null);

      setErrorMessage(
        error.message ||
          "Unable to analyse the architectural plan."
      );
    } finally {
      setIsUploading(false);
    }
  };

  // -----------------------------------------------------------------------
  // Validation helpers
  // -----------------------------------------------------------------------

  const validateConstructionParameters = () => {
    const fields = [
      {
        value: wallHeight,
        name: "wall height",
      },
      {
        value: foundationWidth,
        name: "foundation width",
      },
      {
        value: foundationDepth,
        name: "foundation depth",
      },
      {
        value: slabThickness,
        name: "slab thickness",
      },
      {
        value: hardcoreDepth,
        name: "hardcore depth",
      },
      {
        value: wallThickness,
        name: "wall thickness",
      },
    ];

    for (const field of fields) {
      if (
        field.value === "" ||
        Number(field.value) <= 0
      ) {
        return `Please enter a valid ${field.name}.`;
      }
    }

    if (
      wastagePercentage === "" ||
      Number(wastagePercentage) < 0
    ) {
      return "Please enter a valid material wastage percentage.";
    }

    if (
      reinforcementRuns === "" ||
      Number(reinforcementRuns) <= 0
    ) {
      return "Please enter a valid reinforcement run value.";
    }

    if (
      brickForceInterval === "" ||
      Number(brickForceInterval) <= 0
    ) {
      return "Please enter a valid brick-force interval.";
    }

    if (
      meshAllowance === "" ||
      Number(meshAllowance) < 0
    ) {
      return "Please enter a valid mesh allowance.";
    }

    return "";
  };

  // -----------------------------------------------------------------------
  // Run estimation
  // -----------------------------------------------------------------------

  const handleRunEstimation = async (event) => {
    event.preventDefault();

    setErrorMessage("");

    if (!processedFilename) {
      setErrorMessage(
        "Please analyse the architectural plan first."
      );
      return;
    }

    const parameterError =
      validateConstructionParameters();

    if (parameterError) {
      setErrorMessage(parameterError);
      return;
    }

    setIsEstimating(true);

    try {
      /*
       * The existing API expects the architectural scale and
       * construction information through query parameters.
       *
       * Internal cost calculations are deliberately not exposed
       * through the interface.
       */
      const query = new URLSearchParams({
        project_name: projectName,
        location,
        scale_ratio: String(scaleRatio),
        wall_height_m: String(wallHeight),
        wall_thickness_m: String(wallThickness),
        foundation_width_m: String(foundationWidth),
        foundation_depth_m: String(foundationDepth),
        slab_thickness_m: String(slabThickness),
        hardcore_depth_m: String(hardcoreDepth),
        wastage_percentage: String(wastagePercentage),
        reinforcement_runs: String(reinforcementRuns),
        brick_force_interval_courses: String(brickForceInterval),
        mesh_required: String(meshRequired),
        mesh_allowance_percentage: String(meshAllowance),
        location_profile_id: locationProfile,
        threshold: "0.5",
        currency: "USD",
      });

      const response = await fetch(
        `${API_BASE_URL}/estimation/full/${encodeURIComponent(
          processedFilename
        )}?${query.toString()}`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Estimation failed."
        );
      }

      setResult(data);
      setStep(3);
    } catch (error) {
      setErrorMessage(
        error.message ||
          "Unable to complete the construction estimate."
      );
    } finally {
      setIsEstimating(false);
    }
  };

  // -----------------------------------------------------------------------
  // New project
  // -----------------------------------------------------------------------

  const startNewProject = () => {
    setStep(1);

    setProjectName("");
    setLocation("");

    setLocationProfile(
      DEFAULTS.locationProfile
    );

    setPlanFile(null);
    setStoredFilename("");
    setProcessedFilename("");

    setWallHeight(DEFAULTS.wallHeight);
    setFoundationWidth(
      DEFAULTS.foundationWidth
    );
    setFoundationDepth(
      DEFAULTS.foundationDepth
    );
    setSlabThickness(
      DEFAULTS.slabThickness
    );
    setHardcoreDepth(
      DEFAULTS.hardcoreDepth
    );
    setWallThickness(
      DEFAULTS.wallThickness
    );
    setWastagePercentage(
      DEFAULTS.wastagePercentage
    );

    setReinforcementRuns(
      DEFAULTS.reinforcementRuns
    );
    setBrickForceInterval(
      DEFAULTS.brickForceInterval
    );
    setMeshRequired(true);
    setMeshAllowance(
      DEFAULTS.meshAllowance
    );

    setScaleRatio(DEFAULTS.scaleRatio);

    setResult(null);
    setVisionAnalysis(null);
    setVisionEdits({
      floorArea: "",
      walls: "",
      rooms: "",
      doors: "",
      windows: "",
      wallLength: "",
    });
    setErrorMessage("");
    setMapAnalysisState("idle");
  };

  // -----------------------------------------------------------------------
  // Formatting
  // -----------------------------------------------------------------------

  const formatMoney = (value) => {
    const number = Number(value || 0);

    return `$${number.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const formatNumber = (
    value,
    decimals = 2
  ) => {
    const number = Number(value || 0);

    return number.toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  };

  // -----------------------------------------------------------------------
  // Header
  // -----------------------------------------------------------------------

  const renderHeader = () => (
    <header className="topbar">
      <div>
        <p className="eyebrow">
          Dashboard
        </p>

        <h2>
          ZimBuild AI
        </h2>
      </div>

      <div
        className="system-status"
        style={{
          display: "flex",
          alignItems: "center",
          gap: "14px",
        }}
      >
        <span className="status-dot"></span>
        System ready

        <span
          style={{
            color: "#475569",
            fontSize: "13px",
          }}
        >
          {authUser?.name || authUser?.email || "Signed in"}
        </span>

        <button
          type="button"
          onClick={handleSignOut}
          className="secondary-button"
          style={{
            padding: "8px 12px",
            fontSize: "12px",
          }}
        >
          Sign out
        </button>
      </div>
    </header>
  );

  // -----------------------------------------------------------------------
  // Sidebar
  // -----------------------------------------------------------------------

  const renderSidebar = () => (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">
          Z
        </div>

        <div>
          <h1>
            ZimBuild AI
          </h1>

          <p>
            Construction Intelligence
          </p>
        </div>
      </div>

      <nav className="sidebar-nav">
        <button
          className={`nav-item ${
            step === 1
              ? "active"
              : ""
          }`}
          onClick={() => setStep(1)}
        >
          <span>⌂</span>
          Dashboard
        </button>

        <button
          className="nav-item"
          onClick={startNewProject}
        >
          <span>＋</span>
          New Project
        </button>

        <button
          className="nav-item"
          type="button"
        >
          <span>▣</span>
          Projects
        </button>
      </nav>

      <div className="sidebar-footer">
        <p>
          Automated BoQ
        </p>

        <p>
          & Cost Estimation
        </p>
      </div>
    </aside>
  );

  // -----------------------------------------------------------------------
  // House gallery
  // -----------------------------------------------------------------------

  const renderHouseGallery = () => (
    <section className="house-gallery">
      <div className="gallery-heading">
        <div>
          <p className="eyebrow">
            Build with confidence
          </p>

          <h3>
            From your plan to your future home.
          </h3>
        </div>

        <p>
          Analyse residential architectural plans
          and turn them into structured construction
          quantities and cost estimates.
        </p>
      </div>

      <div className="house-gallery-grid">
        <div
          className="house-image house-image-large"
          style={{
            backgroundImage:
              "url(https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1400&q=85)",
          }}
        >
          <div className="house-overlay">
            <span>
              Modern residential
            </span>
          </div>
        </div>

        <div
          className="house-image"
          style={{
            backgroundImage:
              "url(https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=900&q=85)",
          }}
        >
          <div className="house-overlay">
            <span>
              Contemporary design
            </span>
          </div>
        </div>

        <div
          className="house-image"
          style={{
            backgroundImage:
              "url(https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=900&q=85)",
          }}
        >
          <div className="house-overlay">
            <span>
              Residential architecture
            </span>
          </div>
        </div>

        <div
          className="house-image"
          style={{
            backgroundImage:
              "url(https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?auto=format&fit=crop&w=900&q=85)",
          }}
        >
          <div className="house-overlay">
            <span>
              Future home
            </span>
          </div>
        </div>
      </div>
    </section>
  );

  // -----------------------------------------------------------------------
  // Step indicator
  // -----------------------------------------------------------------------

  const renderStepIndicator = () => (
    <div className="step-indicator">
      <div
        className={
          step >= 1
            ? "step-active"
            : ""
        }
      >
        1
      </div>

      <span
        className={
          step >= 2
            ? "line-active"
            : ""
        }
      ></span>

      <div
        className={
          step >= 2
            ? "step-active"
            : ""
        }
      >
        2
      </div>

      <span
        className={
          step >= 3
            ? "line-active"
            : ""
        }
      ></span>

      <div
        className={
          step >= 3
            ? "step-active"
            : ""
        }
      >
        3
      </div>
    </div>
  );

  // -----------------------------------------------------------------------
  // AI analysis status
  // -----------------------------------------------------------------------

  const renderAnalysisStatus = () => {
    if (mapAnalysisState === "idle") {
      return null;
    }

    if (mapAnalysisState === "analysing") {
      return (
        <div className="analysis-status analysis-running">
          <div className="analysis-spinner"></div>

          <div>
            <strong>
              Analysing architectural plan...
            </strong>

            <span>
              ZimBuild AI is sending the prepared plan to the
              Vision model and extracting walls, rooms, doors,
              windows and floor information.
            </span>
          </div>
        </div>
      );
    }

    return (
      <div className="analysis-status analysis-complete">
        <div className="analysis-check">✓</div>

        <div>
          <strong>Visualisation complete</strong>

          <span>
            The architectural plan has been analysed successfully.
            Review the detected information below before continuing.
          </span>
        </div>
      </div>
    );
  };

  // -----------------------------------------------------------------------
  // Vision analysis summary
  // -----------------------------------------------------------------------

  const renderVisionAnalysisSummary = () => {
    if (!visionAnalysis) {
      return null;
    }

    const walls = visionAnalysis.walls || {};
    const rooms = visionAnalysis.rooms || {};
    const doors = visionAnalysis.doors || {};
    const windows = visionAnalysis.windows || {};
    const floor = visionAnalysis.floor || {};
    const roof = visionAnalysis.roof || {};

    const externalWalls = walls.external_walls || [];
    const internalWalls = walls.internal_walls || [];

    return (
      <section className="project-card details-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">Visualisation result</p>

            <h3>What ZimBuild AI detected</h3>

            <p className="card-subtitle">
              These values come directly from the Vision analysis of
              the uploaded architectural plan.
            </p>
          </div>
        </div>

        <div className="notice-box">
          <strong>Plan analysed successfully</strong>

          <span>
            Please review the detected building information. The
            construction parameters below are separate inputs that
            are supplied by the user for quantity estimation.
          </span>
        </div>

        <div
        className="results-grid"
        style={{
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
        }}
      >
          <div className="result-card">
            <p className="eyebrow">Floor area</p>
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={visionEdits.floorArea}
              onChange={(event) =>
                setVisionEdits((current) => ({
                  ...current,
                  floorArea: event.target.value,
                }))
              }
              aria-label="Corrected floor area"
            />
            <span>recommended floor area (editable)</span>
          </div>

          <div className="result-card">
            <p className="eyebrow">Walls</p>
            <input
              type="number"
              min="0"
              step="1"
              value={visionEdits.walls}
              onChange={(event) =>
                setVisionEdits((current) => ({
                  ...current,
                  walls: event.target.value,
                }))
              }
              aria-label="Corrected wall count"
            />
            <span>detected wall segments (editable)</span>
          </div>

          <div className="result-card">
            <p className="eyebrow">Rooms</p>
            <input
              type="number"
              min="0"
              step="1"
              value={visionEdits.rooms}
              onChange={(event) =>
                setVisionEdits((current) => ({
                  ...current,
                  rooms: event.target.value,
                }))
              }
              aria-label="Corrected room count"
            />
            <span>detected rooms (editable)</span>
          </div>

          <div className="result-card">
            <p className="eyebrow">Windows</p>
            <input
              type="number"
              min="0"
              step="1"
              value={visionEdits.windows}
              onChange={(event) =>
                setVisionEdits((current) => ({
                  ...current,
                  windows: event.target.value,
                }))
              }
              aria-label="Corrected window count"
            />
            <span>detected windows (editable)</span>
          </div>

          <div className="result-card">
            <p className="eyebrow">Wall length</p>
            <div className="input-with-unit">
              <input
                type="number"
                min="0"
                step="0.01"
                value={visionEdits.wallLength}
                onChange={(event) =>
                  setVisionEdits((current) => ({
                    ...current,
                    wallLength: event.target.value,
                  }))
                }
                aria-label="Corrected total wall length"
              />
              <span>m</span>
            </div>
            <span>total detected wall length (editable)</span>
          </div>

          <div className="result-card">
            <p className="eyebrow">Doors</p>
            <input
              type="number"
              min="0"
              step="1"
              value={visionEdits.doors}
              onChange={(event) =>
                setVisionEdits((current) => ({
                  ...current,
                  doors: event.target.value,
                }))
              }
              aria-label="Corrected door count"
            />
            <span>detected doors (editable)</span>
          </div>
        </div>

        <div className="analysis-summary-grid">
          <div>
            <span>External walls</span>
            <strong>
              {externalWalls.length || 0} segments
            </strong>
          </div>

          <div>
            <span>External wall length</span>
            <strong>
              {formatNumber(walls.total_external_wall_length_m ?? 0)} m
            </strong>
          </div>

          <div>
            <span>Internal walls</span>
            <strong>
              {internalWalls.length || 0} segments
            </strong>
          </div>

          <div>
            <span>Internal wall length</span>
            <strong>
              {formatNumber(walls.total_internal_wall_length_m ?? 0)} m
            </strong>
          </div>
        </div>

        <div className="notice-box">
          <strong>
            Roof detection: {roof.present ? "Detected" : "Not detected"}
          </strong>

          <span>
            Roofing is currently excluded from the ZimBuild AI BoQ.
          </span>
        </div>
      </section>
    );
  };

  // -----------------------------------------------------------------------
  // Step 1 - Project + plan
  // -----------------------------------------------------------------------

  const renderProjectStep = () => (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">
            AI-powered construction estimation
          </p>

          <h3>
            Turn architectural plans into
            <span>
              {" "}
              quantities, costs and BoQs.
            </span>
          </h3>

          <p className="hero-description">
            Upload a residential architectural
            plan and ZimBuild AI will analyse
            the drawing, identify relevant
            building information and prepare
            the construction estimate.
          </p>
        </div>
      </section>

      {renderHouseGallery()}

      <section className="project-card">
        <div className="card-header">
          <div>
            <p className="eyebrow">
              Step 1
            </p>

            <h3>
              Analyse your architectural plan
            </h3>
          </div>

          {renderStepIndicator()}
        </div>

        <div className="notice-box">
          <strong>
            Residential plans only
          </strong>

          <span>
            ZimBuild AI is designed for
            residential architectural plans.
            Roofs are currently not detected
            or included in the construction
            estimate.
          </span>
        </div>

        <form
          onSubmit={handleProjectSubmit}
        >
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="projectName">
                Project name
              </label>

              <input
                id="projectName"
                type="text"
                placeholder="e.g. My Family House"
                value={projectName}
                onChange={(event) =>
                  setProjectName(
                    event.target.value
                  )
                }
              />
            </div>

            <div className="form-group">
              <label htmlFor="location">
                Project location
              </label>

              <input
                id="location"
                type="text"
                placeholder="e.g. Gweru"
                value={location}
                onChange={(event) =>
                  setLocation(
                    event.target.value
                  )
                }
              />
            </div>
          </div>

          <div className="form-group upload-group">
            <label>
              Architectural plan
            </label>

            <label
              htmlFor="planUpload"
              className={`upload-area ${
                planFile
                  ? "upload-selected"
                  : ""
              }`}
            >
              <input
                id="planUpload"
                type="file"
                accept=".png,.jpg,.jpeg,.pdf,.piv"
                onChange={
                  handleFileChange
                }
              />

              {planFile?.previewUrl ? (
                <img
                  src={
                    planFile.previewUrl
                  }
                  alt="Selected architectural plan"
                  className="plan-thumbnail"
                />
              ) : (
                <div className="upload-icon">
                  ↑
                </div>
              )}

              {planFile ? (
                <>
                  <strong>
                    {planFile.file.name}
                  </strong>

                  <span>
                    Plan selected successfully
                  </span>

                  <span className="upload-button">
                    Change plan
                  </span>
                </>
              ) : (
                <>
                  <strong>
                    Upload your architectural plan
                  </strong>

                  <span>
                    PNG, JPG, JPEG, PDF or PIV
                  </span>

                  <span className="upload-button">
                    Browse files
                  </span>
                </>
              )}
            </label>
          </div>

          {renderAnalysisStatus()}

          {errorMessage && (
            <div className="error-message">
              {errorMessage}
            </div>
          )}

          <div className="form-actions">
            <p>
              The plan will be analysed before
              additional construction details
              are requested.
            </p>

            <button
              type="submit"
              className="primary-button"
              disabled={
                isUploading ||
                mapAnalysisState ===
                  "analysing"
              }
            >
              {mapAnalysisState ===
              "analysing"
                ? "Analysing map..."
                : mapAnalysisState ===
                  "analysed"
                ? "Map analysed ✓"
                : "Analyse architectural plan"}

              <span>
                →
              </span>
            </button>
          </div>
        </form>
      </section>


    </>
  );

  // -----------------------------------------------------------------------
  // Additional details after map analysis
  // -----------------------------------------------------------------------

  const renderAdditionalDetails = () => (
    <>
      {renderVisionAnalysisSummary()}
      <section className="project-card details-card">
      <div className="card-header">
        <div>
          <p className="eyebrow">
            Map analysis complete
          </p>

          <h3>
            Please enter some additional details
          </h3>

          <p className="card-subtitle">
            Some construction information may
            not be fully visible or reliably
            measurable from the architectural
            drawing. The values below are
            pre-filled with recommended defaults.
          </p>
        </div>
      </div>

      <div className="notice-box">
        <strong>
          Visualisation complete
        </strong>

        <span>
          ZimBuild AI has analysed the uploaded
          plan. Please review the additional
          construction details below. You can
          change any value where you have more
          accurate information.
        </span>
      </div>

      <div className="calibration-section">
        <p className="section-label">
          Drawing scale
        </p>

        <div className="form-group">
          <label htmlFor="scaleRatio">
            Architectural drawing scale
          </label>

          <select
            id="scaleRatio"
            value={scaleRatio}
            onChange={(event) =>
              setScaleRatio(
                event.target.value
              )
            }
          >
            <option value="50">
              1:50
            </option>

            <option value="100">
              1:100
            </option>

            <option value="200">
              1:200
            </option>

            <option value="500">
              1:500
            </option>
          </select>

          <span className="field-help">
            If the scale shown on the drawing
            is different, select the matching
            value.
          </span>
        </div>
      </div>

      <div className="calibration-section">
        <p className="section-label">
          Construction parameters
        </p>

        <p className="section-note">
          Default values are already provided.
          Change them only when you have more
          accurate project information.
        </p>

        <div className="small-form-grid">
          <div className="form-group">
            <label htmlFor="wallHeight">
              Wall height
            </label>

            <div className="input-with-unit">
              <input
                id="wallHeight"
                type="number"
                min="0.1"
                step="0.1"
                value={wallHeight}
                onChange={(event) =>
                  setWallHeight(
                    event.target.value
                  )
                }
              />

              <span>
                m
              </span>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="wallThickness">
              Wall thickness
            </label>

            <div className="input-with-unit">
              <input
                id="wallThickness"
                type="number"
                min="0.05"
                step="0.01"
                value={wallThickness}
                onChange={(event) =>
                  setWallThickness(
                    event.target.value
                  )
                }
              />

              <span>
                m
              </span>
            </div>
          </div>
        </div>

        <div className="small-form-grid">
          <div className="form-group">
            <label htmlFor="foundationWidth">
              Foundation width
            </label>

            <div className="input-with-unit">
              <input
                id="foundationWidth"
                type="number"
                min="0.05"
                step="0.05"
                value={foundationWidth}
                onChange={(event) =>
                  setFoundationWidth(
                    event.target.value
                  )
                }
              />

              <span>
                m
              </span>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="foundationDepth">
              Foundation depth
            </label>

            <div className="input-with-unit">
              <input
                id="foundationDepth"
                type="number"
                min="0.05"
                step="0.05"
                value={foundationDepth}
                onChange={(event) =>
                  setFoundationDepth(
                    event.target.value
                  )
                }
              />

              <span>
                m
              </span>
            </div>
          </div>
        </div>

        <div className="small-form-grid">
          <div className="form-group">
            <label htmlFor="slabThickness">
              Slab thickness
            </label>

            <div className="input-with-unit">
              <input
                id="slabThickness"
                type="number"
                min="0.05"
                step="0.05"
                value={slabThickness}
                onChange={(event) =>
                  setSlabThickness(
                    event.target.value
                  )
                }
              />

              <span>
                m
              </span>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="hardcoreDepth">
              Hardcore depth
            </label>

            <div className="input-with-unit">
              <input
                id="hardcoreDepth"
                type="number"
                min="0.05"
                step="0.05"
                value={hardcoreDepth}
                onChange={(event) =>
                  setHardcoreDepth(
                    event.target.value
                  )
                }
              />

              <span>
                m
              </span>
            </div>
          </div>
        </div>

        <div className="small-form-grid">
          <div className="form-group">
            <label htmlFor="wastage">
              Material allowance
            </label>

            <div className="input-with-unit">
              <input
                id="wastage"
                type="number"
                min="0"
                step="0.5"
                value={wastagePercentage}
                onChange={(event) =>
                  setWastagePercentage(
                    event.target.value
                  )
                }
              />

              <span>
                %
              </span>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="reinforcementRuns">
              Reinforcement runs
            </label>

            <input
              id="reinforcementRuns"
              type="number"
              min="1"
              step="1"
              value={reinforcementRuns}
              onChange={(event) =>
                setReinforcementRuns(
                  event.target.value
                )
              }
            />
          </div>
        </div>
      </div>

      <div className="calibration-section">
        <p className="section-label">
          Masonry and reinforcement
        </p>

        <div className="small-form-grid">
          <div className="form-group">
            <label htmlFor="brickForceInterval">
              Brick-force interval
            </label>

            <div className="input-with-unit">
              <input
                id="brickForceInterval"
                type="number"
                min="1"
                step="1"
                value={brickForceInterval}
                onChange={(event) =>
                  setBrickForceInterval(
                    event.target.value
                  )
                }
              />

              <span>
                courses
              </span>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="meshAllowance">
              Reinforcement mesh allowance
            </label>

            <div className="input-with-unit">
              <input
                id="meshAllowance"
                type="number"
                min="0"
                step="1"
                value={meshAllowance}
                onChange={(event) =>
                  setMeshAllowance(
                    event.target.value
                  )
                }
              />

              <span>
                %
              </span>
            </div>
          </div>
        </div>

        <div className="form-group checkbox-group">
          <label>
            <input
              type="checkbox"
              checked={meshRequired}
              onChange={(event) =>
                setMeshRequired(
                  event.target.checked
                )
              }
            />

            <span>
              Reinforcement mesh required
            </span>
          </label>
        </div>
      </div>

      <div className="calibration-section">
        <p className="section-label">
          Project setting
        </p>

        <div className="form-group">
          <label htmlFor="locationProfile">
            Project location type
          </label>

          <select
            id="locationProfile"
            value={locationProfile}
            onChange={(event) =>
              setLocationProfile(
                event.target.value
              )
            }
          >
            {LOCATION_OPTIONS.map(
              (option) => (
                <option
                  key={option.value}
                  value={option.value}
                >
                  {option.label}
                </option>
              )
            )}
          </select>

          <span className="field-help">
            {selectedLocation.description}
          </span>
        </div>
      </div>

      {errorMessage && (
        <div className="error-message">
          {errorMessage}
        </div>
      )}

      <div className="form-actions">
        <button
          type="button"
          className="secondary-button"
          onClick={() => {
            setMapAnalysisState(
              "idle"
            );
            setProcessedFilename("");
          }}
        >
          ← Analyse another plan
        </button>

        <button
          type="button"
          className="primary-button"
          disabled={isEstimating}
          onClick={handleRunEstimation}
        >
          {isEstimating
            ? "Preparing estimate..."
            : "Continue to estimate"}

          <span>
            →
          </span>
        </button>
      </div>
      </section>
    </>
  );

  // -----------------------------------------------------------------------
  // Results - project summary and complete BoQ
  // -----------------------------------------------------------------------

  const renderResultsStep = () => {
    const phase8 = result?.phase8 || {};
    const phase9 = result?.phase9 || {};
    const phase10 = result?.phase10 || {};
    const phase11 = result?.phase11 || {};
    const phase12 = result?.phase12 || {};

    const grandTotal =
      phase12?.grand_total ??
      phase11?.grand_total ??
      result?.grand_total ??
      0;

    const materialSubtotal =
      phase12?.material_subtotal ??
      phase12?.subtotal ??
      phase11?.material_subtotal ??
      0;

    const labourTotal =
      phase12?.labour_total ??
      phase11?.labour_total ??
      0;

    const transportTotal =
      phase12?.transport_total ??
      phase11?.transport_total ??
      0;

    const stageResults = phase11?.stages || phase10?.stages || [];
    const boqItems = phase12?.items || [];

    return (
      <>
        <section className="results-header">
          <div>
            <p className="eyebrow">Estimation complete</p>
            <h3>
              {result?.project?.project_name || projectName}
            </h3>
            <p>
              {result?.project?.location || location}
            </p>
          </div>

          {renderStepIndicator()}
        </section>

        <section className="results-total-card">
          <div>
            <p className="eyebrow">Final estimated construction cost</p>
            <h4>{formatMoney(grandTotal)}</h4>
            <p>
              Materials, labour, transport and the selected location
              adjustment are included.
            </p>
          </div>

          <button
            className="secondary-button"
            onClick={startNewProject}
          >
            + New project
          </button>
        </section>

        <section className="results-grid">
          <div className="result-card">
            <p className="eyebrow">Rooms</p>
            <strong>{phase8?.rooms?.count ?? 0}</strong>
            <span>detected rooms</span>
          </div>

          <div className="result-card">
            <p className="eyebrow">Walls</p>
            <strong>{phase8?.walls?.count ?? 0}</strong>
            <span>detected wall segments</span>
          </div>

          <div className="result-card">
            <p className="eyebrow">Doors / Windows</p>
            <strong>
              {phase8?.doors?.count ?? 0} / {phase8?.windows?.count ?? 0}
            </strong>
            <span>detected openings</span>
          </div>

          <div className="result-card">
            <p className="eyebrow">Floor area</p>
            <strong>
              {formatNumber(
                phase8?.floor?.recommended_floor_area_m2 ??
                  phase9?.building?.floor_area_m2 ??
                  0
              )} m²
            </strong>
            <span>analysed floor area</span>
          </div>
        </section>

        <section className="result-card large-result-card">
          <div className="results-section-header">
            <div>
              <p className="eyebrow">AI analysis</p>
              <h3>Architectural plan summary</h3>
            </div>
          </div>

          <div className="analysis-summary-grid">
            <div>
              <span>External wall length</span>
              <strong>
                {formatNumber(
                  phase8?.walls?.total_external_wall_length_m ?? 0
                )} m
              </strong>
            </div>

            <div>
              <span>Internal wall length</span>
              <strong>
                {formatNumber(
                  phase8?.walls?.total_internal_wall_length_m ?? 0
                )} m
              </strong>
            </div>

            <div>
              <span>Total wall length</span>
              <strong>
                {formatNumber(
                  phase8?.walls?.total_wall_length_m ?? 0
                )} m
              </strong>
            </div>

            <div>
              <span>Plan scale</span>
              <strong>
                {result?.scale?.scale_label || `1:${scaleRatio}`}
              </strong>
            </div>
          </div>
        </section>

        <section className="result-card large-result-card">
          <div className="results-section-header">
            <div>
              <p className="eyebrow">Construction stages</p>
              <h3>Four-stage cost breakdown</h3>
            </div>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Stage</th>
                  <th>Materials</th>
                  <th>Labour</th>
                  <th>Transport</th>
                  <th>Stage total</th>
                </tr>
              </thead>
              <tbody>
                {stageResults.map((stage) => (
                  <tr key={`${stage.stage_number}-${stage.stage_name}`}>
                    <td>{stage.stage_name}</td>
                    <td>{formatMoney(stage.material_subtotal)}</td>
                    <td>{formatMoney(stage.labour_cost)}</td>
                    <td>{formatMoney(stage.transport_cost)}</td>
                    <td>{formatMoney(stage.stage_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="result-card large-result-card">
          <div className="results-section-header">
            <div>
              <p className="eyebrow">Bill of quantities</p>
              <h3>Priced BoQ items</h3>
            </div>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>No.</th>
                  <th>Stage</th>
                  <th>Description</th>
                  <th>Quantity</th>
                  <th>Rate</th>
                  <th>Amount</th>
                </tr>
              </thead>
              <tbody>
                {boqItems.map((item, index) => (
                  <tr key={`${item.item_number || index}-${item.description}`}>
                    <td>{item.item_number || index + 1}</td>
                    <td>{item.stage_name || "-"}</td>
                    <td>{item.description || item.material_name}</td>
                    <td>
                      {formatNumber(item.quantity)} {item.unit}
                    </td>
                    <td>{formatMoney(item.unit_rate)}</td>
                    <td>{formatMoney(item.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="result-card large-result-card">
          <div className="results-section-header">
            <div>
              <p className="eyebrow">Cost summary</p>
              <h3>Complete project cost</h3>
            </div>
          </div>

          <div className="boq-total-row">
            <span>Material subtotal</span>
            <strong>{formatMoney(materialSubtotal)}</strong>
          </div>

          <div className="boq-total-row">
            <span>Labour</span>
            <strong>{formatMoney(labourTotal)}</strong>
          </div>

          <div className="boq-total-row">
            <span>Transport</span>
            <strong>{formatMoney(transportTotal)}</strong>
          </div>

          <div className="boq-total-row">
            <span>Base project cost</span>
            <strong>
              {formatMoney(phase12?.base_project_cost ?? phase11?.base_project_cost ?? 0)}
            </strong>
          </div>

          <div className="boq-total-row">
            <span>
              Location adjustment ({
                phase12?.location || phase11?.location?.name || selectedLocation.label
              })
            </span>
          </div>

          <div className="boq-total-row grand-total">
            <span>Final estimated cost</span>
            <strong>{formatMoney(grandTotal)}</strong>
          </div>
        </section>

        <section className="result-card">
          <div className="results-section-header">
            <div>
              <p className="eyebrow">Project information</p>
              <h3>Estimate configuration</h3>
            </div>
          </div>

          <div className="analysis-summary-grid">
            <div>
              <span>Location</span>
              <strong>{location}</strong>
            </div>

            <div>
              <span>Location type</span>
              <strong>
                {selectedLocation.label}
              </strong>
            </div>

            <div>
              <span>Wall height</span>
              <strong>{wallHeight} m</strong>
            </div>

            <div>
              <span>Plan scale</span>
              <strong>
                {result?.scale?.scale_label || `1:${scaleRatio}`}
              </strong>
            </div>
          </div>
        </section>
      </>
    );
  };

  // -----------------------------------------------------------------------
  // Main render
  // -----------------------------------------------------------------------

  if (!authUser) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "24px",
          background: "#f6f8fb",
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: "440px",
            padding: "40px",
            background: "#ffffff",
            borderRadius: "20px",
            boxShadow: "0 18px 60px rgba(15, 23, 42, 0.12)",
            textAlign: "center",
          }}
        >
          <div
            style={{
              width: "56px",
              height: "56px",
              margin: "0 auto 18px",
              borderRadius: "14px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "#111827",
              color: "#ffffff",
              fontSize: "24px",
              fontWeight: 800,
            }}
          >
            Z
          </div>

          <p className="eyebrow">Welcome to ZimBuild AI</p>

          <h2 style={{ margin: "0 0 10px" }}>
            Sign in to continue
          </h2>

          <p
            style={{
              margin: "0 auto 28px",
              maxWidth: "340px",
              color: "#64748b",
              lineHeight: 1.6,
            }}
          >
            Sign in with your Google account to access your
            construction projects and estimates.
          </p>

          {!GOOGLE_CLIENT_ID ? (
            <div className="error-message">
              Google Sign-In is not configured on this deployment yet.
            </div>
          ) : (
            <>
              <div
                ref={googleButtonRef}
                style={{
                  minHeight: "44px",
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                }}
              />

              {authLoading && (
                <p
                  style={{
                    marginTop: "16px",
                    color: "#64748b",
                  }}
                >
                  Signing you in...
                </p>
              )}
            </>
          )}

          {authError && (
            <div
              className="error-message"
              style={{ marginTop: "16px" }}
            >
              {authError}
            </div>
          )}

          <p
            style={{
              marginTop: "28px",
              fontSize: "12px",
              color: "#94a3b8",
            }}
          >
            Secure authentication powered by Google.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      {renderSidebar()}

      <main className="main-content">
        {renderHeader()}

        {step === 1 &&
          renderProjectStep()}

        {step === 2 &&
          renderAdditionalDetails()}

        {step === 3 &&
          renderResultsStep()}
      </main>
    </div>
  );
}

export default App;
