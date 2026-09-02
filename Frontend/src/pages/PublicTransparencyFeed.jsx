import { useState } from "react";
import { useOperational } from "../context/OperationalContext";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { IconFeed, IconThumbsUp, IconShieldCheck, IconSearch, IconPlus, IconCheckCircle, IconX } from "../components/Icons";

export default function PublicTransparencyFeed() {
  const { feed, applaudPost, addCommentToFeed, addFeedPost } = useOperational();
  const { user } = useAuth();
  const { notify } = useToast();

  const [search, setSearch] = useState("");
  const [wardFilter, setWardFilter] = useState("All");

  // Comment input per feed post
  const [commentInputs, setCommentInputs] = useState({});
  // Modal for new post
  const [showAddPostModal, setShowAddPostModal] = useState(false);

  const [newPost, setNewPost] = useState({
    title: "",
    location: "",
    ward: "Ward 12",
    resolvedBy: "SmartSweep Rapid Crew",
    wasteRemoved: "1.2 Tons",
    hazardAddressed: "Foul Smell & Obstruction",
    beforePhoto: "https://images.unsplash.com/photo-1530587191325-3db32d826c18?auto=format&fit=crop&w=600&q=80",
    afterPhoto: "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?auto=format&fit=crop&w=600&q=80",
  });

  // Calculate Metrics
  const totalApplauds = feed.reduce((acc, curr) => acc + curr.applauds, 0);

  const filteredFeed = feed.filter((post) => {
    const q = search.trim().toLowerCase();
    const matchesSearch =
      !q ||
      post.title.toLowerCase().includes(q) ||
      post.location.toLowerCase().includes(q) ||
      post.resolvedBy.toLowerCase().includes(q) ||
      post.hazardAddressed.toLowerCase().includes(q);
    const matchesWard = wardFilter === "All" || post.ward === wardFilter;
    return matchesSearch && matchesWard;
  });

  const handleApplaud = (id, title) => {
    applaudPost(id);
    notify(`Applauded cleanup for "${title}"! 👏`, "success");
  };

  const handleAddComment = (e, postId) => {
    e.preventDefault();
    const text = commentInputs[postId];
    if (!text || !text.trim()) return;

    addCommentToFeed(postId, user ? user.name : "Citizen User", text.trim());
    notify("Comment published on public feed!", "info");
    setCommentInputs({ ...commentInputs, [postId]: "" });
  };

  const handleCreatePost = (e) => {
    e.preventDefault();
    if (!newPost.title || !newPost.location) {
      notify("Please provide a title and location for the post.", "error");
      return;
    }
    addFeedPost(newPost);
    notify("New transparency post published to community feed!", "success");
    setNewPost({
      title: "",
      location: "",
      ward: "Ward 12",
      resolvedBy: "SmartSweep Rapid Crew",
      wasteRemoved: "1.2 Tons",
      hazardAddressed: "Foul Smell & Obstruction",
      beforePhoto: "https://images.unsplash.com/photo-1530587191325-3db32d826c18?auto=format&fit=crop&w=600&q=80",
      afterPhoto: "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?auto=format&fit=crop&w=600&q=80",
    });
    setShowAddPostModal(false);
  };

  return (
    <div className="page page-wide">
      <div className="page-header">
        <div>
          <span className="eyebrow">Public Accountability</span>
          <h1>Public Transparency & Impact Feed</h1>
          <p className="page-lead">
            Real-time audit log of municipal cleanup milestones, before-and-after transformations, verified waste collection stats, and citizen feedback.
          </p>
        </div>
        <div className="page-actions">
          <button className="primary-btn" onClick={() => setShowAddPostModal(true)}>
            <IconPlus /> Publish Milestone
          </button>
        </div>
      </div>

      {/* Community Impact Metrics Banner */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-icon green"><IconShieldCheck /></div>
          <div>
            <span className="kpi-value">100% Verified</span>
            <span className="kpi-label">Audited Cleanups</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon accent"><IconFeed /></div>
          <div>
            <span className="kpi-value">4.3 Tons</span>
            <span className="kpi-label">Waste Cleared This Week</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon blue"><IconThumbsUp /></div>
          <div>
            <span className="kpi-value">{totalApplauds}</span>
            <span className="kpi-label">Citizen Applauds</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon amber"><IconCheckCircle /></div>
          <div>
            <span className="kpi-value">98.4%</span>
            <span className="kpi-label">Resolution Rate</span>
          </div>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="dashboard-toolbar">
        <div className="search-wrap">
          <IconSearch />
          <input
            type="text"
            className="search-input"
            placeholder="Search cleanups, wards, hazard resolutions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button className="search-clear-btn" onClick={() => setSearch("")}>
              <IconX />
            </button>
          )}
        </div>
        <div className="filters">
          {["All", "Ward 04", "Ward 08", "Ward 12"].map((w) => (
            <button
              key={w}
              className={wardFilter === w ? "active" : ""}
              onClick={() => setWardFilter(w)}
            >
              {w}
            </button>
          ))}
        </div>
      </div>

      {/* Feed List */}
      <div className="feed-list">
        {filteredFeed.length === 0 ? (
          <div className="empty-state">No transparency updates found matching your search.</div>
        ) : (
          filteredFeed.map((post) => (
            <div key={post.id} className="feed-card">
              <div className="feed-card-header">
                <div className="feed-author-info">
                  <div className="feed-avatar"><IconShieldCheck /></div>
                  <div>
                    <div className="feed-title-wrap">
                      <h3>{post.title}</h3>
                      {post.verified && (
                        <span className="verified-badge">
                          <IconShieldCheck /> Verified Resolution
                        </span>
                      )}
                    </div>
                    <p className="feed-meta">
                      {post.location} • <span className="ward-tag">{post.ward}</span> • {post.completedAt}
                    </p>
                  </div>
                </div>
                <button
                  className="applaud-btn"
                  onClick={() => handleApplaud(post.id, post.title)}
                >
                  <IconThumbsUp /> <span>{post.applauds} Applauds</span>
                </button>
              </div>

              {/* Before & After Comparison Showcase */}
              <div className="visual-comparison">
                <div className="comparison-item">
                  <span className="comparison-badge before">BEFORE REPORT</span>
                  <img src={post.beforePhoto} alt="Before cleanup" />
                </div>
                <div className="comparison-item">
                  <span className="comparison-badge after">AFTER CLEANUP</span>
                  <img src={post.afterPhoto} alt="After cleanup" />
                </div>
              </div>

              {/* Resolution Stats Pills */}
              <div className="feed-stats-bar">
                <div className="stat-pill">
                  <span className="stat-label">Crew Lead:</span>
                  <span className="stat-val">{post.resolvedBy}</span>
                </div>
                <div className="stat-pill">
                  <span className="stat-label">Waste Removed:</span>
                  <span className="stat-val highlight">{post.wasteRemoved}</span>
                </div>
                <div className="stat-pill">
                  <span className="stat-label">Hazard Addressed:</span>
                  <span className="stat-val">{post.hazardAddressed}</span>
                </div>
              </div>

              {/* Comments Section */}
              <div className="feed-comments-section">
                <h4>Citizen Feedback ({post.comments.length})</h4>
                <div className="comment-list">
                  {post.comments.map((c) => (
                    <div key={c.id} className="comment-bubble">
                      <div className="comment-header">
                        <span className="comment-user">{c.user}</span>
                        <span className="comment-time">{c.time}</span>
                      </div>
                      <p className="comment-text">{c.text}</p>
                    </div>
                  ))}
                </div>

                <form onSubmit={(e) => handleAddComment(e, post.id)} className="comment-input-row">
                  <input
                    type="text"
                    placeholder="Write a message of thanks or feedback..."
                    value={commentInputs[post.id] || ""}
                    onChange={(e) =>
                      setCommentInputs({ ...commentInputs, [post.id]: e.target.value })
                    }
                  />
                  <button type="submit" className="primary-btn btn-sm">Comment</button>
                </form>
              </div>
            </div>
          ))
        )}
      </div>

      {/* MODAL: Add Transparency Post */}
      {showAddPostModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>Publish Transparency Milestone</h2>
              <button className="icon-btn" onClick={() => setShowAddPostModal(false)}><IconX /></button>
            </div>
            <form onSubmit={handleCreatePost} className="complaint-form">
              <label>
                Cleanup Milestone Title
                <input
                  type="text"
                  required
                  placeholder="e.g. Indiranagar Market Waste Drive"
                  value={newPost.title}
                  onChange={(e) => setNewPost({ ...newPost, title: e.target.value })}
                />
              </label>
              <label>
                Location Details
                <input
                  type="text"
                  required
                  placeholder="e.g. 10th Main, Indiranagar"
                  value={newPost.location}
                  onChange={(e) => setNewPost({ ...newPost, location: e.target.value })}
                />
              </label>
              <label>
                Ward
                <select
                  value={newPost.ward}
                  onChange={(e) => setNewPost({ ...newPost, ward: e.target.value })}
                >
                  <option value="Ward 04">Ward 04 (MG Road)</option>
                  <option value="Ward 08">Ward 08 (Koramangala)</option>
                  <option value="Ward 12">Ward 12 (Indiranagar)</option>
                </select>
              </label>
              <label>
                Resolved By (Crew / Lead)
                <input
                  type="text"
                  required
                  placeholder="e.g. Crew Alpha & Vehicle KA-01-EV-9012"
                  value={newPost.resolvedBy}
                  onChange={(e) => setNewPost({ ...newPost, resolvedBy: e.target.value })}
                />
              </label>
              <label>
                Quantity Waste Collected
                <input
                  type="text"
                  required
                  placeholder="e.g. 1.8 Tons"
                  value={newPost.wasteRemoved}
                  onChange={(e) => setNewPost({ ...newPost, wasteRemoved: e.target.value })}
                />
              </label>
              <label>
                Hazard Mitigated
                <input
                  type="text"
                  required
                  placeholder="e.g. Mosquito Breeding & Foul Smell"
                  value={newPost.hazardAddressed}
                  onChange={(e) => setNewPost({ ...newPost, hazardAddressed: e.target.value })}
                />
              </label>
              <div className="modal-actions">
                <button type="button" className="secondary-btn" onClick={() => setShowAddPostModal(false)}>Cancel</button>
                <button type="submit" className="primary-btn">Publish to Feed</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
