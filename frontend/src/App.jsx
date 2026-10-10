import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE_URL = "https://zimbuild-ai.onrender.com";
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";

const getAuthHeaders = () => {
  const token = localStorage.getItem("zimbuild_auth_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

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
  const [step, setStep] = useState(5);
  const [showWhatWeDo, setShowWhatWeDo] = useState(false);

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
  const [showSignOutDialog, setShowSignOutDialog] = useState(false);
  const [adminLoginOpen, setAdminLoginOpen] = useState(false);
  const [adminEmail, setAdminEmail] = useState("zimbuildadmin@gmail.com");
  const [adminPassword, setAdminPassword] = useState("");
  const [adminDashboard, setAdminDashboard] = useState(null);
  const [adminDashboardLoading, setAdminDashboardLoading] = useState(false);
  const [adminDashboardError, setAdminDashboardError] = useState("");
  const [userProjects, setUserProjects] = useState([]);
  const [userProjectsLoading, setUserProjectsLoading] = useState(false);
  const [userProjectsError, setUserProjectsError] = useState("");
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
    if (authUser || !GOOGLE_CLIENT_ID || adminLoginOpen) {
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
  }, [authUser, adminLoginOpen]);

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

  const handleAdminLogin = async (event) => {
    event.preventDefault();
    setAuthLoading(true);
    setAuthError("");

    try {
      const response = await fetch(`${API_BASE_URL}/auth/admin/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: adminEmail.trim().toLowerCase(),
          password: adminPassword,
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.detail ||
            (response.status === 404
              ? "Administrator sign-in is not connected yet. The secure admin endpoint must be added to the backend first."
              : "Administrator sign-in failed. Check your details and try again.")
        );
      }

      if (!data.user || data.user.role !== "admin" || !data.token) {
        throw new Error(
          "The server did not return a verified administrator session."
        );
      }

      localStorage.setItem("zimbuild_auth_user", JSON.stringify(data.user));
      localStorage.setItem("zimbuild_auth_token", data.token);
      setAuthUser(data.user);
      setAdminPassword("");
      setAdminLoginOpen(false);
    } catch (error) {
      setAuthError(
        error.message || "Unable to sign in as administrator."
      );
    } finally {
      setAuthLoading(false);
    }
  };

  const loadAdminDashboard = async () => {
    setAdminDashboardLoading(true);
    setAdminDashboardError("");

    try {
      const token = localStorage.getItem("zimbuild_auth_token");
      const response = await fetch(`${API_BASE_URL}/admin/dashboard`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.detail ||
            (response.status === 404
              ? "The administrator dashboard API has not been added to the backend yet."
              : "Could not load administrator dashboard data.")
        );
      }

      setAdminDashboard(data);
    } catch (error) {
      setAdminDashboardError(
        error.message || "Could not load administrator dashboard data."
      );
    } finally {
      setAdminDashboardLoading(false);
    }
  };

  const loadUserProjects = async () => {
    setUserProjectsLoading(true);
    setUserProjectsError("");
    try {
      const response = await fetch(`${API_BASE_URL}/plans/mine`, {
        headers: getAuthHeaders(),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || "Could not load your past projects.");
      }
      setUserProjects(Array.isArray(data.projects) ? data.projects : []);
    } catch (error) {
      setUserProjectsError(error.message || "Could not load your past projects.");
    } finally {
      setUserProjectsLoading(false);
    }
  };

  const downloadBoqPdf = async (estimateId, projectName = "project") => {
    if (!estimateId) {
      setErrorMessage("A saved estimate is required before downloading a BoQ.");
      return;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/boq/${estimateId}/pdf`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "The BoQ PDF could not be downloaded.");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `ZimBuild_BoQ_${String(projectName).replace(/[^a-z0-9_-]/gi, "_")}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setErrorMessage(error.message || "The BoQ PDF could not be downloaded.");
    }
  };

  const openPastProject = (project) => {
    if (!project?.result) {
      setUserProjectsError("This project has no saved estimate to reopen yet.");
      return;
    }
    setResult({
      ...project.result,
      database: {
        ...(project.result.database || {}),
        estimate_id: project.estimate_id,
        plan_id: project.plan_id,
        saved: true,
      },
    });
    setProjectName(project.project_name || "");
    setLocation(project.location || "");
    setStep(3);
  };

  const handleSignOut = () => {
    setShowSignOutDialog(true);
  };

  const confirmSignOut = () => {
    localStorage.removeItem("zimbuild_auth_user");
    localStorage.removeItem("zimbuild_auth_token");
    setAuthUser(null);
    setAuthError("");
    setAdminPassword("");
    setAdminLoginOpen(false);
    setAdminDashboard(null);
    setAdminDashboardError("");
    setShowSignOutDialog(false);
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

  useEffect(() => {
    if (authUser?.role === "admin") {
      loadAdminDashboard();
    }
  }, [authUser?.role]);

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
        headers: getAuthHeaders(),
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
        headers: getAuthHeaders(),
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
        headers: getAuthHeaders(),
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
          headers: getAuthHeaders(),
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
    setShowWhatWeDo(false);
    window.scrollTo({ top: 0, behavior: "smooth" });

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
          type="button"
          className={`nav-item ${step === 5 ? "active" : ""}`}
          onClick={() => {
            setStep(5);
            setShowWhatWeDo(false);
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
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
          className={`nav-item ${step === 4 ? "active" : ""}`}
          type="button"
          onClick={() => {
            setStep(4);
            loadUserProjects();
          }}
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
  // Step 1 - Project + plan
  // -----------------------------------------------------------------------

  const renderProjectStep = () => (
    <>
      <section className="notice-box" style={{ marginBottom: "22px" }}>
        <strong>New project</strong>
        <span>Enter your project details and upload a residential architectural plan to generate quantities, costs and a bill of quantities.</span>
      </section>

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

  const renderUserProjects = () => (
    <section className="project-card">
      <div className="card-header">
        <div>
          <p className="eyebrow">Project library</p>
          <h3>Your past projects</h3>
          <p className="card-subtitle">Your saved estimates are private to your account.</p>
        </div>
        <button type="button" className="secondary-button" onClick={loadUserProjects} disabled={userProjectsLoading}>
          {userProjectsLoading ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      {userProjectsError && <div className="error-message" role="alert">{userProjectsError}</div>}
      {userProjectsLoading ? (
        <p>Loading your saved projects…</p>
      ) : userProjects.length === 0 ? (
        <div className="notice-box"><strong>No saved projects yet</strong><span>When you complete an estimate, it will appear here.</span></div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead><tr><th>Project</th><th>Location</th><th>Status</th><th>Estimated cost</th><th>Date</th><th>Actions</th></tr></thead>
            <tbody>
              {userProjects.map((project) => (
                <tr key={project.estimate_id || project.plan_id}>
                  <td>{project.project_name}</td>
                  <td>{project.location || "—"}</td>
                  <td>{project.status}</td>
                  <td>{project.total_cost == null ? "Not estimated" : `${project.currency || "USD"} ${Number(project.total_cost).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}</td>
                  <td>{project.created_at ? new Date(project.created_at).toLocaleDateString() : "—"}</td>
                  <td>
                    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                      {project.result && <button type="button" className="secondary-button" onClick={() => openPastProject(project)}>View</button>}
                      {project.estimate_id && <button type="button" className="primary-button" onClick={() => downloadBoqPdf(project.estimate_id, project.project_name)}>Download PDF</button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="form-actions">
        <button type="button" className="primary-button" onClick={startNewProject}>+ New project</button>
      </div>
    </section>
  );

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

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            {result?.database?.estimate_id && (
              <button
                type="button"
                className="primary-button"
                onClick={() => downloadBoqPdf(result.database.estimate_id, result?.project?.project_name || projectName)}
              >
                Download BoQ PDF
              </button>
            )}
            <button
              className="secondary-button"
              onClick={startNewProject}
            >
              + New project
            </button>
          </div>
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

          <div className="boq-total-row grand-total">
            <span>Final estimated cost (including materials)</span>
            <strong>{formatMoney(grandTotal)}</strong>
          </div>

          <div className="boq-total-row">
            <span>Labour</span>
            <strong>{formatMoney(labourTotal)}</strong>
          </div>

          <div className="boq-total-row">
            <span>Transport</span>
            <strong>{formatMoney(transportTotal)}</strong>
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
    const loginPrimaryButton = {
      width: "100%",
      minHeight: "48px",
      borderRadius: "10px",
      border: "1px solid #cbd5e1",
      background: "#ffffff",
      color: "#0f172a",
      fontSize: "14px",
      fontWeight: 650,
      cursor: authLoading ? "wait" : "pointer",
      opacity: authLoading ? 0.7 : 1,
    };

    return (
      <div
        className="zimbuild-login-layout"
        style={{
          minHeight: "100vh",
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.08fr) minmax(360px, 0.92fr)",
          background: "#f8fafc",
          fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        }}
      >
        <section
          className="zimbuild-login-brand-panel"
          style={{
            position: "relative",
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            minHeight: "100vh",
            padding: "clamp(28px, 5vw, 68px)",
            color: "#ffffff",
            background: "radial-gradient(circle at 78% 22%, rgba(59,130,246,0.45), transparent 28%), radial-gradient(circle at 16% 84%, rgba(14,165,233,0.2), transparent 30%), linear-gradient(145deg, #07152e 0%, #0b2b63 52%, #1749a6 100%)",
          }}
        >
          <div
            aria-hidden="true"
            style={{
              position: "absolute",
              inset: 0,
              opacity: 0.14,
              pointerEvents: "none",
              backgroundImage: "linear-gradient(rgba(255,255,255,.22) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.22) 1px, transparent 1px)",
              backgroundSize: "42px 42px",
              maskImage: "linear-gradient(to bottom, black, transparent 88%)",
            }}
          />

          <div style={{ position: "relative", zIndex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
              <div
                aria-label="ZimBuild AI architectural logo"
                style={{
                  width: "54px",
                  height: "54px",
                  display: "grid",
                  placeItems: "center",
                  flexShrink: 0,
                  borderRadius: "16px",
                  background: "rgba(255,255,255,0.12)",
                  border: "1px solid rgba(255,255,255,0.28)",
                  boxShadow: "0 12px 32px rgba(0,0,0,0.18)",
                }}
              >
                <svg width="38" height="38" viewBox="0 0 48 48" fill="none" aria-hidden="true">
                  <path d="M7 21.5 24 7l17 14.5v18H7v-18Z" stroke="white" strokeWidth="2.6" strokeLinejoin="round"/>
                  <path d="M16 39V25h16v14M16 25l8-7 8 7M24 25v14" stroke="#93C5FD" strokeWidth="2.4" strokeLinejoin="round"/>
                  <path d="M12 15.5V10h6" stroke="#60A5FA" strokeWidth="2.4" strokeLinecap="round"/>
                </svg>
              </div>
              <div>
                <div style={{ fontSize: "21px", fontWeight: 800, letterSpacing: "-0.5px" }}>ZimBuild AI</div>
                <div style={{ marginTop: "3px", fontSize: "12px", color: "#bfdbfe", letterSpacing: "0.3px" }}>CONSTRUCTION INTELLIGENCE</div>
              </div>
            </div>
          </div>

          <div style={{ position: "relative", zIndex: 1, maxWidth: "660px", padding: "64px 0" }}>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 12px",
                borderRadius: "999px",
                border: "1px solid rgba(191,219,254,0.3)",
                background: "rgba(30,64,175,0.28)",
                color: "#dbeafe",
                fontSize: "11px",
                fontWeight: 750,
                letterSpacing: "1.5px",
              }}
            >
              <span style={{ width: "7px", height: "7px", borderRadius: "50%", background: "#60a5fa" }} />
              AI-POWERED CONSTRUCTION ESTIMATION
            </div>
            <h1 style={{ margin: "28px 0 18px", maxWidth: "650px", fontSize: "clamp(38px, 4.5vw, 66px)", lineHeight: 1.04, letterSpacing: "-2.5px", fontWeight: 820 }}>
              Build smarter.
              <br />
              <span style={{ color: "#93c5fd" }}>Estimate with</span>
              <br />
              confidence.
            </h1>
            <p style={{ maxWidth: "520px", margin: 0, color: "#dbeafe", fontSize: "16px", lineHeight: 1.8 }}>
              Turn residential architectural plans into structured quantities, material costs and bills of quantities — with a workflow designed for construction in Zimbabwe.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "12px", marginTop: "36px", maxWidth: "570px" }}>
              {[
                ["01", "Plan analysis"],
                ["02", "Material quantities"],
                ["03", "Cost estimates"],
              ].map(([number, label]) => (
                <div key={number} style={{ padding: "15px 14px", borderRadius: "12px", background: "rgba(255,255,255,0.08)", border: "1px solid rgba(191,219,254,0.18)" }}>
                  <div style={{ fontSize: "11px", fontWeight: 800, color: "#93c5fd", letterSpacing: "1px" }}>{number}</div>
                  <div style={{ marginTop: "7px", fontSize: "12px", fontWeight: 650, color: "#ffffff" }}>{label}</div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ position: "relative", zIndex: 1, display: "flex", justifyContent: "space-between", gap: "18px", flexWrap: "wrap", color: "#bfdbfe", fontSize: "11px" }}>
            <span>© {new Date().getFullYear()} ZimBuild AI</span>
            <span>Residential construction intelligence</span>
          </div>
        </section>

        <section
          style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "clamp(24px, 5vw, 64px)",
            background: "linear-gradient(180deg, #f8fafc 0%, #eef4fb 100%)",
          }}
        >
          <div style={{ width: "100%", maxWidth: "430px" }}>
            <div style={{ marginBottom: "30px" }}>
              <p style={{ margin: "0 0 10px", color: "#2563eb", fontSize: "11px", fontWeight: 800, letterSpacing: "1.7px", textTransform: "uppercase" }}>
                {adminLoginOpen ? "Secure administrator access" : "Welcome to ZimBuild AI"}
              </p>
              <h2 style={{ margin: 0, color: "#0f172a", fontSize: "clamp(28px, 3vw, 36px)", lineHeight: 1.15, letterSpacing: "-1px", fontWeight: 800 }}>
                {adminLoginOpen ? "Administrator login" : "Sign in to continue"}
              </h2>
              <p style={{ margin: "13px 0 0", color: "#64748b", fontSize: "14px", lineHeight: 1.75 }}>
                {adminLoginOpen
                  ? "Sign in with your administrator credentials to manage ZimBuild AI."
                  : "Access your construction projects, architectural plans and estimates."}
              </p>
            </div>

            <div style={{ padding: "clamp(22px, 3vw, 32px)", borderRadius: "20px", background: "#ffffff", border: "1px solid #e2e8f0", boxShadow: "0 20px 55px rgba(15,23,42,0.08)" }}>
              {adminLoginOpen ? (
                <form onSubmit={handleAdminLogin}>
                  <label htmlFor="admin-email" style={{ display: "block", marginBottom: "8px", color: "#334155", fontSize: "12px", fontWeight: 700 }}>Administrator email</label>
                  <input
                    id="admin-email"
                    type="email"
                    autoComplete="username"
                    required
                    value={adminEmail}
                    onChange={(event) => setAdminEmail(event.target.value)}
                    placeholder="admin@example.com"
                    style={{ boxSizing: "border-box", width: "100%", height: "48px", marginBottom: "18px", padding: "0 13px", border: "1px solid #cbd5e1", borderRadius: "10px", outlineColor: "#2563eb", fontSize: "14px", color: "#0f172a", background: "#fff" }}
                  />
                  <label htmlFor="admin-password" style={{ display: "block", marginBottom: "8px", color: "#334155", fontSize: "12px", fontWeight: 700 }}>Password</label>
                  <input
                    id="admin-password"
                    type="password"
                    autoComplete="current-password"
                    required
                    value={adminPassword}
                    onChange={(event) => setAdminPassword(event.target.value)}
                    placeholder="Enter administrator password"
                    style={{ boxSizing: "border-box", width: "100%", height: "48px", marginBottom: "18px", padding: "0 13px", border: "1px solid #cbd5e1", borderRadius: "10px", outlineColor: "#2563eb", fontSize: "14px", color: "#0f172a", background: "#fff" }}
                  />
                  <button type="submit" disabled={authLoading} style={{ ...loginPrimaryButton, border: "1px solid #1d4ed8", background: "linear-gradient(135deg, #2563eb, #1d4ed8)", color: "#ffffff", boxShadow: "0 8px 18px rgba(37,99,235,0.22)" }}>
                    {authLoading ? "Verifying administrator…" : "Sign in as administrator"}
                  </button>
                  <button type="button" onClick={() => { setAdminLoginOpen(false); setAdminPassword(""); setAuthError(""); }} style={{ ...loginPrimaryButton, marginTop: "12px", background: "#f8fafc" }}>
                    Back to Google sign-in
                  </button>
                </form>
              ) : (
                <>
                  {!GOOGLE_CLIENT_ID ? (
                    <div className="error-message">Google Sign-In is not configured on this deployment yet.</div>
                  ) : (
                    <>
                      <div ref={googleButtonRef} style={{ minHeight: "48px", display: "flex", justifyContent: "center", alignItems: "center" }} />
                      {authLoading && <p style={{ margin: "14px 0 0", textAlign: "center", color: "#64748b", fontSize: "13px" }}>Signing you in securely…</p>}
                    </>
                  )}

                  <div style={{ display: "flex", alignItems: "center", gap: "12px", margin: "25px 0 20px", color: "#94a3b8", fontSize: "11px" }}>
                    <span style={{ height: "1px", flex: 1, background: "#e2e8f0" }} />
                    <span>ADMINISTRATOR ACCESS</span>
                    <span style={{ height: "1px", flex: 1, background: "#e2e8f0" }} />
                  </div>

                  <button
                    type="button"
                    onClick={() => { setAdminLoginOpen(true); setAuthError(""); }}
                    style={{ ...loginPrimaryButton, display: "flex", alignItems: "center", justifyContent: "center", gap: "10px", background: "#f8fafc" }}
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <path d="M12 3 5 6v5c0 4.5 2.9 8 7 10 4.1-2 7-5.5 7-10V6l-7-3Z" stroke="#1d4ed8" strokeWidth="1.8" strokeLinejoin="round"/>
                      <path d="m9 12 2 2 4-4" stroke="#1d4ed8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    Administrator login
                  </button>
                </>
              )}

              {authError && (
                <div className="error-message" role="alert" style={{ marginTop: "16px" }}>
                  {authError}
                </div>
              )}

              <p style={{ margin: "22px 0 0", color: "#94a3b8", fontSize: "11px", lineHeight: 1.6, textAlign: "center" }}>
                {adminLoginOpen
                  ? "Administrator access is verified by the secure ZimBuild AI server."
                  : "Secure authentication powered by Google."}
              </p>
            </div>

            <p style={{ margin: "22px 0 0", color: "#94a3b8", fontSize: "11px", lineHeight: 1.6, textAlign: "center" }}>
              By continuing, you agree to use ZimBuild AI responsibly for construction planning and estimation.
            </p>
          </div>
        </section>

        <style>{`
          @media (max-width: 850px) {
            .zimbuild-login-layout { grid-template-columns: 1fr !important; }
            .zimbuild-login-brand-panel { min-height: auto !important; }
          }
          @media (max-width: 520px) {
            .zimbuild-login-layout { display: block !important; }
            .zimbuild-login-brand-panel { padding: 28px 24px !important; }
          }
        `}</style>
      </div>
    );
  }

  if (authUser?.role === "admin") {
    return (
      <div style={{ minHeight: "100vh", display: "flex", background: "#f1f5f9", color: "#0f172a", fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif" }}>
        <aside style={{ width: "250px", flexShrink: 0, display: "flex", flexDirection: "column", padding: "26px 18px", color: "#fff", background: "#0f172a" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", padding: "0 8px 30px" }}>
            <div style={{ width: "42px", height: "42px", display: "grid", placeItems: "center", borderRadius: "12px", background: "#2563eb" }}>
              <svg width="30" height="30" viewBox="0 0 48 48" fill="none" aria-hidden="true"><path d="M7 21.5 24 7l17 14.5v18H7v-18Z" stroke="white" strokeWidth="2.6" strokeLinejoin="round"/><path d="M16 39V25h16v14M16 25l8-7 8 7M24 25v14" stroke="#bfdbfe" strokeWidth="2.4" strokeLinejoin="round"/></svg>
            </div>
            <div><div style={{ fontSize: "16px", fontWeight: 800 }}>ZimBuild AI</div><div style={{ marginTop: "3px", color: "#94a3b8", fontSize: "10px" }}>ADMIN CONSOLE</div></div>
          </div>
          <div style={{ padding: "0 10px", color: "#94a3b8", fontSize: "10px", fontWeight: 800, letterSpacing: "1.4px" }}>MANAGEMENT</div>
          <div style={{ marginTop: "14px", padding: "13px 12px", borderRadius: "10px", background: "#1d4ed8", fontSize: "13px", fontWeight: 700 }}>▦ &nbsp; Overview</div>
          <div style={{ flex: 1 }} />
          <div style={{ padding: "14px 10px", borderTop: "1px solid #334155", color: "#cbd5e1", fontSize: "12px", overflowWrap: "anywhere" }}>{authUser.email}</div>
          <button type="button" onClick={handleSignOut} style={{ marginTop: "10px", minHeight: "42px", borderRadius: "9px", border: "1px solid #475569", background: "transparent", color: "#fff", fontWeight: 650, cursor: "pointer" }}>Sign out</button>
        </aside>
        <main style={{ flex: 1, minWidth: 0, padding: "clamp(24px, 4vw, 48px)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "20px", flexWrap: "wrap", paddingBottom: "24px", borderBottom: "1px solid #dbe3ed" }}>
            <div><p style={{ margin: "0 0 8px", color: "#2563eb", fontSize: "11px", fontWeight: 800, letterSpacing: "1.4px" }}>ADMINISTRATOR DASHBOARD</p><h1 style={{ margin: 0, fontSize: "clamp(26px, 3vw, 34px)", letterSpacing: "-1px" }}>Welcome back</h1><p style={{ margin: "10px 0 0", color: "#64748b", fontSize: "14px" }}>Manage architectural plan activity and estimation records.</p></div>
            <button type="button" onClick={loadAdminDashboard} disabled={adminDashboardLoading} style={{ padding: "11px 16px", border: "1px solid #1d4ed8", borderRadius: "9px", background: "#2563eb", color: "#fff", fontSize: "13px", fontWeight: 700, cursor: "pointer" }}>{adminDashboardLoading ? "Refreshing…" : "Refresh dashboard"}</button>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: "16px", marginTop: "28px" }}>
            {[
              ["Past plans", adminDashboard?.total_plans ?? "—", "Uploaded architectural plans"],
              ["Estimates", adminDashboard?.total_estimates ?? "—", "Generated cost estimates"],
              ["Registered users", adminDashboard?.total_users ?? "—", "Accounts using ZimBuild AI"],
            ].map(([label, value, detail]) => (
              <div key={label} style={{ padding: "22px", borderRadius: "14px", border: "1px solid #e2e8f0", background: "#fff", boxShadow: "0 4px 14px rgba(15,23,42,.03)" }}>
                <div style={{ color: "#64748b", fontSize: "12px", fontWeight: 650 }}>{label}</div>
                <div style={{ marginTop: "12px", color: "#0f172a", fontSize: "30px", fontWeight: 800 }}>{value}</div>
                <div style={{ marginTop: "7px", color: "#94a3b8", fontSize: "11px" }}>{detail}</div>
              </div>
            ))}
          </div>
          <section style={{ marginTop: "24px", padding: "24px", borderRadius: "14px", border: "1px solid #e2e8f0", background: "#fff" }}>
            <h2 style={{ margin: "0 0 8px", fontSize: "18px" }}>Recent architectural plans</h2>
            <p style={{ margin: "0 0 18px", color: "#64748b", fontSize: "13px", lineHeight: 1.6 }}>Recent plans and estimates across all accounts.</p>
            {adminDashboardError && <div className="error-message" role="alert">{adminDashboardError}</div>}
            {adminDashboardLoading && <p style={{ color: "#64748b", fontSize: "13px" }}>Loading administrator records…</p>}
            {!adminDashboardLoading && !adminDashboardError && (adminDashboard?.recent_projects || []).length === 0 && (
              <div style={{ padding: "30px 18px", textAlign: "center", borderRadius: "10px", border: "1px dashed #cbd5e1", background: "#f8fafc" }}>No plans have been recorded yet.</div>
            )}
            {!adminDashboardLoading && !adminDashboardError && (adminDashboard?.recent_projects || []).length > 0 && (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                  <thead><tr>{["Project", "Location", "User", "Status", "Estimate", "Created", "BoQ"].map((label) => <th key={label} style={{ padding: "12px 10px", textAlign: "left", borderBottom: "1px solid #e2e8f0", color: "#64748b", whiteSpace: "nowrap" }}>{label}</th>)}</tr></thead>
                  <tbody>
                    {adminDashboard.recent_projects.map((project) => (
                      <tr key={project.estimate_id || project.plan_id}>
                        <td style={{ padding: "12px 10px", borderBottom: "1px solid #f1f5f9" }}>{project.project_name}</td>
                        <td style={{ padding: "12px 10px", borderBottom: "1px solid #f1f5f9" }}>{project.location}</td>
                        <td style={{ padding: "12px 10px", borderBottom: "1px solid #f1f5f9" }}>{project.user_email}</td>
                        <td style={{ padding: "12px 10px", borderBottom: "1px solid #f1f5f9" }}>{project.status}</td>
                        <td style={{ padding: "12px 10px", borderBottom: "1px solid #f1f5f9", whiteSpace: "nowrap" }}>{project.total_cost == null ? "—" : `${project.currency || "USD"} ${Number(project.total_cost).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}</td>
                        <td style={{ padding: "12px 10px", borderBottom: "1px solid #f1f5f9", whiteSpace: "nowrap" }}>{project.created_at ? new Date(project.created_at).toLocaleDateString() : "—"}</td>
                        <td style={{ padding: "12px 10px", borderBottom: "1px solid #f1f5f9" }}>{project.estimate_id ? <button type="button" onClick={() => downloadBoqPdf(project.estimate_id, project.project_name)} style={{ padding: "7px 9px", border: "1px solid #bfdbfe", borderRadius: "7px", background: "#eff6ff", color: "#1d4ed8", cursor: "pointer", whiteSpace: "nowrap" }}>PDF</button> : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </main>
        {showSignOutDialog && (
          <div role="presentation" onClick={() => setShowSignOutDialog(false)} style={{ position: "fixed", inset: 0, zIndex: 10000, display: "flex", alignItems: "center", justifyContent: "center", padding: "24px", background: "rgba(15,23,42,.62)", backdropFilter: "blur(4px)" }}>
            <section role="alertdialog" aria-modal="true" aria-labelledby="signout-dialog-title" aria-describedby="signout-dialog-description" onClick={(event) => event.stopPropagation()} style={{ width: "100%", maxWidth: "440px", overflow: "hidden", borderRadius: "18px", background: "#fff", boxShadow: "0 24px 70px rgba(15,23,42,.3)" }}>
              <div style={{ padding: "24px 26px 22px", color: "#fff", background: "linear-gradient(135deg,#1d4ed8,#2563eb,#1e40af)" }}><strong style={{ fontSize: "11px", letterSpacing: "1.5px" }}>ZIMBUILD AI</strong><h2 id="signout-dialog-title" style={{ margin: "8px 0 0", fontSize: "21px" }}>Sign out of ZimBuild AI?</h2></div>
              <div style={{ padding: "24px 26px 26px" }}><p id="signout-dialog-description" style={{ margin: 0, color: "#475569", fontSize: "14px", lineHeight: 1.7 }}>Are you sure you want to exit ZimBuild AI? You will need to sign in again to access your construction projects and estimates.</p><div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "26px" }}><button type="button" onClick={() => setShowSignOutDialog(false)} style={{ padding: "11px 18px", borderRadius: "9px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", fontSize: "13px", fontWeight: 650, cursor: "pointer" }}>Stay signed in</button><button type="button" onClick={confirmSignOut} style={{ padding: "11px 18px", borderRadius: "9px", border: "1px solid #1d4ed8", background: "#2563eb", color: "#fff", fontSize: "13px", fontWeight: 700, cursor: "pointer" }}>Yes, sign out</button></div></div>
            </section>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="app-shell">
      {renderSidebar()}

      <main className="main-content">
        {renderHeader()}

        {step === 5 &&
          renderDashboardHome()}

        {step === 1 &&
          renderProjectStep()}

        {step === 2 &&
          renderAdditionalDetails()}

        {step === 3 &&
          renderResultsStep()}

        {step === 4 &&
          renderUserProjects()}
      </main>

      {showSignOutDialog && (
        <div
          role="presentation"
          onClick={() => setShowSignOutDialog(false)}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 10000,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
            background: "rgba(15, 23, 42, 0.62)",
            backdropFilter: "blur(4px)",
          }}
        >
          <section
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="signout-dialog-title"
            aria-describedby="signout-dialog-description"
            onClick={(event) => event.stopPropagation()}
            style={{
              width: "100%",
              maxWidth: "440px",
              overflow: "hidden",
              borderRadius: "18px",
              background: "#ffffff",
              boxShadow: "0 24px 70px rgba(15, 23, 42, 0.3)",
              border: "1px solid rgba(191, 219, 254, 0.9)",
            }}
          >
            <div
              style={{
                padding: "24px 26px 22px",
                color: "#ffffff",
                background: "linear-gradient(135deg, #1d4ed8 0%, #2563eb 55%, #1e40af 100%)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "14px",
                }}
              >
                <div
                  aria-hidden="true"
                  style={{
                    width: "46px",
                    height: "46px",
                    flexShrink: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: "13px",
                    background: "rgba(255, 255, 255, 0.16)",
                    border: "1px solid rgba(255, 255, 255, 0.28)",
                    fontSize: "22px",
                    fontWeight: 800,
                  }}
                >
                  Z
                </div>
                <div>
                  <p
                    style={{
                      margin: 0,
                      fontSize: "11px",
                      fontWeight: 700,
                      letterSpacing: "1.5px",
                      textTransform: "uppercase",
                      color: "#dbeafe",
                    }}
                  >
                    ZimBuild AI
                  </p>
                  <h2
                    id="signout-dialog-title"
                    style={{
                      margin: "5px 0 0",
                      fontSize: "21px",
                      lineHeight: 1.3,
                      fontWeight: 750,
                      color: "#ffffff",
                    }}
                  >
                    Sign out of ZimBuild AI?
                  </h2>
                </div>
              </div>
            </div>

            <div style={{ padding: "24px 26px 26px" }}>
              <p
                id="signout-dialog-description"
                style={{
                  margin: 0,
                  color: "#475569",
                  fontSize: "14px",
                  lineHeight: 1.7,
                }}
              >
                Are you sure you want to exit ZimBuild AI? You will need to
                sign in again to access your construction projects and estimates.
              </p>

              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: "12px",
                  marginTop: "26px",
                }}
              >
                <button
                  type="button"
                  onClick={() => setShowSignOutDialog(false)}
                  style={{
                    padding: "11px 18px",
                    borderRadius: "9px",
                    border: "1px solid #cbd5e1",
                    background: "#ffffff",
                    color: "#334155",
                    fontSize: "13px",
                    fontWeight: 650,
                    cursor: "pointer",
                  }}
                >
                  Stay signed in
                </button>
                <button
                  type="button"
                  onClick={confirmSignOut}
                  style={{
                    padding: "11px 18px",
                    borderRadius: "9px",
                    border: "1px solid #1d4ed8",
                    background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
                    color: "#ffffff",
                    fontSize: "13px",
                    fontWeight: 700,
                    boxShadow: "0 4px 12px rgba(37, 99, 235, 0.24)",
                    cursor: "pointer",
                  }}
                >
                  Yes, sign out
                </button>
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

export default App;
