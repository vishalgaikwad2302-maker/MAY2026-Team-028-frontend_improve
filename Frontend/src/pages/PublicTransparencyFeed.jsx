import { useState, useEffect, useCallback } from "react";
import { useOperational } from "../context/OperationalContext";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import {
  IconThumbsUp,
  IconShieldCheck,
  IconSearch,
  IconPlus,
  IconX,
  IconFeed,
} from "../components/Icons";
import { compressImage, formatBytes, fileToDataUrl } from "../utils/imageCompressor";
import {
  getFeedPostsApi,
  createTransparencyPostApi,
  uploadPhotoApi,
  applaudTransparencyPostApi,
  addTransparencyCommentApi,
  getMediaUrl,
} from "../utils/api";

export default function PublicTransparencyFeed() {
  const { feed: localFeed, applaudPost: localApplaudPost, addFeedPost: localAddFeedPost } = useOperational();
  const { user } = useAuth();
  const { notify } = useToast();

  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  // Modal for new post
  const [showAddPostModal, setShowAddPostModal] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [selectedImages, setSelectedImages] = useState([]); // [{ file, previewUrl, compressedSize, originalSize }]
  const [isCompressing, setIsCompressing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Lightbox for full image viewing
  const [activeLightboxImg, setActiveLightboxImg] = useState(null);

  // Comments state & visibility toggles per post
  const [expandedComments, setExpandedComments] = useState({});
  const [commentInputs, setCommentInputs] = useState({});

  // Fetch posts from backend or fallback to local context
  const loadPosts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getFeedPostsApi(1, 40);
      const localItems = (localFeed || []).map((p) => ({
        ...p,
        authorName: p.authorName || p.resolvedBy || "Community Member",
        description:
          p.description ||
          (p.wasteRemoved
            ? `${p.location ? `${p.location} • ` : ""}Cleared ${p.wasteRemoved}${p.hazardAddressed ? ` (${p.hazardAddressed})` : ""}`
            : ""),
        date: p.date || p.completedAt || "Recent",
      }));

      if (res.success && Array.isArray(res.data?.items)) {
        const backendItems = res.data.items.map((p) => ({
          ...p,
          authorName: p.author_name || (p.complaint_id ? "SmartSweep Crew" : "Community Member"),
          verified: !!p.complaint_id,
          applauds: p.applause_count || 0,
          comments: p.comments || [],
          date: p.created_at
            ? new Date(p.created_at).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
                year: "numeric",
              })
            : "Recent",
        }));

        // Merge: keep local mock or offline posts that are not present in backend
        const backendIds = new Set(backendItems.map((p) => String(p.id)));
        const uniqueLocals = localItems.filter((lp) => !backendIds.has(String(lp.id)));

        setPosts([...uniqueLocals, ...backendItems]);
      } else {
        // Fallback to local context feed
        setPosts(localItems);
      }
    } catch {
      setPosts(
        (localFeed || []).map((p) => ({
          ...p,
          authorName: p.authorName || p.resolvedBy || "Community Member",
          date: p.date || p.completedAt || "Recent",
        }))
      );
    } finally {
      setLoading(false);
    }
  }, [localFeed]);

  useEffect(() => {
    loadPosts();
  }, [loadPosts]);

  // Handle image selection & auto-compression under 200 KB
  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    if (selectedImages.length + files.length > 3) {
      notify("You can upload a maximum of 3 photos.", "error");
      return;
    }

    setIsCompressing(true);
    const newItems = [];

    for (const file of files) {
      if (!file.type.startsWith("image/")) {
        notify(`Skipped "${file.name}": Only image files are allowed.`, "warning");
        continue;
      }

      try {
        // Automatically compress to <= 200 KB
        const compressed = await compressImage(file, { maxKB: 200, maxDimension: 1600 });
        newItems.push({
          file: compressed.file,
          previewUrl: compressed.previewUrl,
          originalSize: compressed.originalSize,
          compressedSize: compressed.compressedSize,
          savingsPercent: compressed.savingsPercent,
          name: file.name,
        });
      } catch (err) {
        console.error("Compression error:", err);
        notify(`Could not process "${file.name}".`, "error");
      }
    }

    setSelectedImages((prev) => [...prev, ...newItems].slice(0, 3));
    setIsCompressing(false);
    e.target.value = ""; // Reset input so same file can be re-selected if needed
  };

  const removeImage = (indexToRemove) => {
    setSelectedImages((prev) => {
      const removed = prev[indexToRemove];
      if (removed?.previewUrl) {
        URL.revokeObjectURL(removed.previewUrl);
      }
      return prev.filter((_, idx) => idx !== indexToRemove);
    });
  };

  // Clean up preview URLs when modal closes or unmounts
  const resetForm = () => {
    selectedImages.forEach((img) => {
      if (img.previewUrl) URL.revokeObjectURL(img.previewUrl);
    });
    setSelectedImages([]);
    setTitle("");
    setDescription("");
    setShowAddPostModal(false);
    setIsSubmitting(false);
    setIsCompressing(false);
  };

  // Handle Submitting a New Minimal Post
  const handleCreatePost = async (e) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      notify("Please provide both a title and a description.", "error");
      return;
    }

    if (!user) {
      notify("Please log in to publish a transparency update.", "warning");
      return;
    }

    setIsSubmitting(true);

    try {
      // 1. Upload compressed photos (or fallback to compressed data URLs)
      const uploadedImageUrls = [];
      for (const img of selectedImages) {
        try {
          const uploadRes = await uploadPhotoApi(img.file);
          if (uploadRes.success && uploadRes.url) {
            uploadedImageUrls.push(uploadRes.url);
          } else {
            const dataUrl = await fileToDataUrl(img.file);
            uploadedImageUrls.push(dataUrl);
          }
        } catch {
          const dataUrl = await fileToDataUrl(img.file);
          uploadedImageUrls.push(dataUrl);
        }
      }

      // 2. Try calling backend API (if server is available)
      let backendId = null;
      try {
        const payload = {
          title: title.trim(),
          description: description.trim(),
          images: uploadedImageUrls.filter((u) => !u.startsWith("data:")),
        };
        const apiRes = await createTransparencyPostApi(payload);
        if (apiRes.success && apiRes.data?.id) {
          backendId = apiRes.data.id;
        }
      } catch {
        // Backend offline or static host
      }

      const postId = backendId || `F-${Date.now()}`;
      const createdPost = {
        id: postId,
        title: title.trim(),
        description: description.trim(),
        images: uploadedImageUrls,
        applauds: 0,
        authorName: user.name || user.full_name || "Community Member",
        verified: user.role === "crew" || user.role === "admin",
        date: "Just now",
        comments: [],
      };

      // Optimistically prepend to active posts list
      setPosts((prev) => [createdPost, ...prev.filter((p) => String(p.id) !== String(postId))]);

      // Sync to local operational context and localStorage
      localAddFeedPost({
        ...createdPost,
        resolvedBy: user.name || user.full_name || "Community Member",
      });

      notify("Transparency update published successfully! ✨", "success");
      resetForm();
    } catch (err) {
      console.error("Failed to publish post:", err);
      notify("Failed to publish post. Please check your connection.", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Applaud post
  const handleApplaud = async (postId, postTitle) => {
    // Optimistic local update
    setPosts((prev) =>
      prev.map((p) =>
        p.id === postId
          ? { ...p, applauds: (p.applauds || p.applause_count || 0) + 1 }
          : p
      )
    );
    localApplaudPost(postId);
    notify(`Applauded "${postTitle}"! 👏`, "success");

    // Call backend API in background
    if (typeof postId === "number" || !String(postId).startsWith("F-")) {
      try {
        await applaudTransparencyPostApi(postId);
      } catch {
        // background sync failure ignored
      }
    }
  };

  // Toggle comments
  const toggleComments = (postId) => {
    setExpandedComments((prev) => ({
      ...prev,
      [postId]: !prev[postId],
    }));
  };

  // Add Comment
  const handleAddComment = async (e, postId) => {
    e.preventDefault();
    const text = (commentInputs[postId] || "").trim();
    if (!text) return;

    const newComment = {
      id: Date.now(),
      user: user ? user.name || user.full_name : "Citizen User",
      text,
      time: "Just now",
    };

    // Optimistically update comment list on post
    setPosts((prev) =>
      prev.map((p) => {
        if (p.id === postId) {
          return {
            ...p,
            comments: [...(p.comments || []), newComment],
          };
        }
        return p;
      })
    );

    setCommentInputs((prev) => ({ ...prev, [postId]: "" }));
    notify("Comment posted!", "info");

    // Call API if server-backed post
    if (typeof postId === "number" || !String(postId).startsWith("F-")) {
      try {
        await addTransparencyCommentApi(postId, text);
      } catch {
        // sync error
      }
    }
  };

  // Filtered posts based on minimal search
  const filteredPosts = posts.filter((p) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      (p.title && p.title.toLowerCase().includes(q)) ||
      (p.description && p.description.toLowerCase().includes(q)) ||
      (p.authorName && p.authorName.toLowerCase().includes(q))
    );
  });

  // Render responsive media gallery (1, 2, or 3 images)
  const renderMediaGallery = (post) => {
    // Normalise images: check post.images array first, else fallback to legacy before/after
    const imgs = [];
    if (Array.isArray(post.images) && post.images.length > 0) {
      imgs.push(...post.images);
    } else if (typeof post.images === "string" && post.images.trim()) {
      try {
        const parsed = JSON.parse(post.images);
        if (Array.isArray(parsed)) imgs.push(...parsed);
        else imgs.push(post.images);
      } catch {
        imgs.push(post.images);
      }
    } else {
      if (post.beforePhoto) imgs.push(post.beforePhoto);
      if (post.afterPhoto) imgs.push(post.afterPhoto);
      if (post.before_photo_url) imgs.push(post.before_photo_url);
      if (post.after_photo_url) imgs.push(post.after_photo_url);
    }

    const uniqueImgs = Array.from(new Set(imgs)).slice(0, 3);
    if (!uniqueImgs.length) return null;

    if (uniqueImgs.length === 1) {
      return (
        <div
          className="minimal-gallery-1"
          onClick={() => setActiveLightboxImg(uniqueImgs[0])}
          title="Click to expand photo"
        >
          <img src={getMediaUrl(uniqueImgs[0])} alt="Update photo" loading="lazy" />
        </div>
      );
    }

    if (uniqueImgs.length === 2) {
      return (
        <div className="minimal-gallery-2">
          {uniqueImgs.map((imgUrl, idx) => (
            <div
              key={idx}
              className="gallery-item"
              onClick={() => setActiveLightboxImg(imgUrl)}
              title="Click to expand photo"
            >
              <img src={getMediaUrl(imgUrl)} alt={`Update photo ${idx + 1}`} loading="lazy" />
            </div>
          ))}
        </div>
      );
    }

    // 3 images: 1 dominant hero on left + 2 stacked on right
    return (
      <div className="minimal-gallery-3">
        <div
          className="gallery-main"
          onClick={() => setActiveLightboxImg(uniqueImgs[0])}
          title="Click to expand photo"
        >
          <img src={getMediaUrl(uniqueImgs[0])} alt="Update photo 1" loading="lazy" />
        </div>
        <div className="gallery-stacked">
          <div
            className="gallery-sub"
            onClick={() => setActiveLightboxImg(uniqueImgs[1])}
            title="Click to expand photo"
          >
            <img src={getMediaUrl(uniqueImgs[1])} alt="Update photo 2" loading="lazy" />
          </div>
          <div
            className="gallery-sub"
            onClick={() => setActiveLightboxImg(uniqueImgs[2])}
            title="Click to expand photo"
          >
            <img src={getMediaUrl(uniqueImgs[2])} alt="Update photo 3" loading="lazy" />
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="page minimal-feed-page">
      {/* Minimal Header */}
      <div className="minimal-feed-header">
        <div>
          <span className="eyebrow">Community Transparency</span>
          <h1>Transparency Feed</h1>
          <p className="page-lead">
            Verified municipal cleanup milestones and neighborhood community updates.
          </p>
        </div>
        <button
          className="primary-btn"
          onClick={() => {
            if (!user) {
              notify("Please log in to publish a community update.", "warning");
              return;
            }
            setShowAddPostModal(true);
          }}
        >
          <IconPlus /> New Post
        </button>
      </div>

      {/* Minimal Search */}
      <div className="minimal-search-bar">
        <IconSearch />
        <input
          type="text"
          placeholder="Search updates by title or description..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {search && (
          <button
            className="search-clear-btn"
            onClick={() => setSearch("")}
            title="Clear search"
          >
            <IconX />
          </button>
        )}
      </div>

      {/* Posts Stream */}
      <div className="minimal-feed-stream">
        {loading ? (
          <div className="empty-state">Loading transparency updates...</div>
        ) : filteredPosts.length === 0 ? (
          <div className="empty-state">
            <IconFeed />
            <p>No transparency updates found.</p>
          </div>
        ) : (
          filteredPosts.map((post) => {
            const commentCount = (post.comments || []).length;
            const isCommentsOpen = !!expandedComments[post.id];

            return (
              <div key={post.id} className="minimal-post-card">
                {/* Post Header */}
                <div className="minimal-post-header">
                  <div className="minimal-post-author">
                    <div className="feed-avatar">
                      <IconShieldCheck />
                    </div>
                    <div>
                      <div className="feed-author-name">
                        <span>{post.authorName}</span>
                        {post.verified && (
                          <span className="verified-badge">
                            <IconShieldCheck /> Verified
                          </span>
                        )}
                      </div>
                      <span className="minimal-post-date">{post.date}</span>
                    </div>
                  </div>

                  <button
                    className="applaud-btn"
                    onClick={() => handleApplaud(post.id, post.title)}
                    title="Applaud this cleanup"
                  >
                    <IconThumbsUp />
                    <span>{post.applauds || post.applause_count || 0}</span>
                  </button>
                </div>

                {/* Post Title & Description */}
                <h3 className="minimal-post-title">{post.title}</h3>
                {post.description && (
                  <p className="minimal-post-description">{post.description}</p>
                )}

                {/* Responsive Image Gallery (1-3 images) */}
                {renderMediaGallery(post)}

                {/* Comments Section */}
                <div className="feed-comments-section">
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      cursor: "pointer",
                      marginBottom: isCommentsOpen ? "0.75rem" : 0,
                    }}
                    onClick={() => toggleComments(post.id)}
                  >
                    <h4 style={{ margin: 0 }}>
                      Feedback {commentCount > 0 ? `(${commentCount})` : ""}
                    </h4>
                    <span style={{ fontSize: "0.8rem", color: "var(--accent)" }}>
                      {isCommentsOpen ? "Hide Feedback" : commentCount > 0 ? "View Feedback" : "Leave Feedback"}
                    </span>
                  </div>

                  {isCommentsOpen && (
                    <>
                      {post.comments && post.comments.length > 0 && (
                        <div className="comment-list">
                          {post.comments.map((c, idx) => (
                            <div key={c.id || idx} className="comment-bubble">
                              <div className="comment-header">
                                <span className="comment-user">{c.user}</span>
                                <span className="comment-time">{c.time}</span>
                              </div>
                              <p className="comment-text">{c.text || c.comment}</p>
                            </div>
                          ))}
                        </div>
                      )}

                      <form
                        onSubmit={(e) => handleAddComment(e, post.id)}
                        className="comment-input-row"
                      >
                        <input
                          type="text"
                          placeholder="Write a message of thanks or feedback..."
                          value={commentInputs[post.id] || ""}
                          onChange={(e) =>
                            setCommentInputs({
                              ...commentInputs,
                              [post.id]: e.target.value,
                            })
                          }
                        />
                        <button type="submit" className="primary-btn btn-sm">
                          Comment
                        </button>
                      </form>
                    </>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* MINIMAL MODAL: Publish Update */}
      {showAddPostModal && (
        <div className="modal-overlay" onClick={resetForm}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Publish Community Update</h2>
              <button className="icon-btn" onClick={resetForm} title="Close">
                <IconX />
              </button>
            </div>

            <form onSubmit={handleCreatePost} className="complaint-form">
              {/* Field 1: Title */}
              <label>
                <span>
                  Update Title <span className="required-star">*</span>
                </span>
                <input
                  type="text"
                  required
                  placeholder="e.g. Indiranagar Market Waste Clearance"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  maxLength={200}
                />
              </label>

              {/* Field 2: Description */}
              <label>
                <span>
                  Description <span className="required-star">*</span>
                </span>
                <textarea
                  required
                  rows={4}
                  placeholder="Describe the cleanup, work completed, or impact..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  maxLength={3000}
                />
              </label>

              {/* Field 3: Image Uploads (Up to 3, Auto-compressed < 200 KB) */}
              <div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "0.4rem",
                  }}
                >
                  <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-h)" }}>
                    Photos (Optional, Up to 3)
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>
                    {selectedImages.length}/3 photos
                  </span>
                </div>

                {selectedImages.length < 3 && (
                  <label className="minimal-dropzone">
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      multiple
                      onChange={handleFileSelect}
                      disabled={isCompressing || isSubmitting}
                      style={{ display: "none" }}
                    />
                    <IconPlus />
                    <div className="dropzone-text">
                      <strong>Click to upload photos</strong>
                      <small>JPG, PNG, WEBP • Auto-compressed strictly under 200 KB</small>
                    </div>
                  </label>
                )}

                {isCompressing && (
                  <div className="compressing-indicator">
                    <div className="spinner-small" />
                    <span>Compressing photo to &lt;200 KB...</span>
                  </div>
                )}

                {selectedImages.length > 0 && (
                  <div className="compressed-previews-grid">
                    {selectedImages.map((img, idx) => (
                      <div key={idx} className="preview-thumb-card">
                        <img src={img.previewUrl} alt={`Selected ${idx + 1}`} />
                        <div className="preview-thumb-info">
                          <span className="preview-size-badge">
                            ✓ {formatBytes(img.compressedSize)}
                          </span>
                        </div>
                        <button
                          type="button"
                          className="remove-thumb-btn"
                          onClick={() => removeImage(idx)}
                          title="Remove photo"
                        >
                          <IconX />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Modal Actions */}
              <div className="modal-actions" style={{ marginTop: "1rem" }}>
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={resetForm}
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="primary-btn"
                  disabled={isSubmitting || isCompressing}
                >
                  {isSubmitting ? "Publishing..." : "Publish Post"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* LIGHTBOX: View Full Image */}
      {activeLightboxImg && (
        <div className="lightbox-overlay" onClick={() => setActiveLightboxImg(null)}>
          <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
            <button
              className="lightbox-close-btn"
              onClick={() => setActiveLightboxImg(null)}
              title="Close full view"
            >
              <IconX />
            </button>
            <img src={getMediaUrl(activeLightboxImg)} alt="Enlarged view" />
          </div>
        </div>
      )}
    </div>
  );
}
