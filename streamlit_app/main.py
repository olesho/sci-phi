import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="PDF Processor", page_icon="📄", layout="wide")

st.title("📄 PDF Processor Dashboard")

# API base URL
API_BASE_URL = "http://localhost:8000"

def get_all_pdfs():
    """Fetch all processed PDFs from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/pdfs")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching PDFs: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return None

def get_stats():
    """Fetch processing statistics from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/stats")
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException:
        return None

def trigger_conversion(uri):
    """Trigger conversion for a specific PDF."""
    try:
        response = requests.post(f"{API_BASE_URL}/convert/{uri}")
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return None

def delete_pdf(uri):
    """Delete a PDF record by URI."""
    try:
        response = requests.delete(f"{API_BASE_URL}/pdfs/{uri}")
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return None

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choose a page", ["📋 PDF List", "➕ Process New PDF", "📊 Statistics", "🔄 Conversion Queue"])

if page == "📋 PDF List":
    st.header("Processed PDFs")
    
    # Add refresh button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Fetch all PDFs
    pdf_data = get_all_pdfs()
    
    if pdf_data and pdf_data.get("pdfs"):
        pdfs = pdf_data["pdfs"]
        st.success(f"Found {pdf_data['count']} processed PDFs")
        
        # Convert to DataFrame for better display
        df_data = []
        for pdf in pdfs:
            # Determine conversion status
            is_converted = pdf.get("is_converted", False)
            conversion_status = "✅ Converted" if is_converted else "⏳ Pending"
            if pdf.get("conversion_error"):
                conversion_status = "❌ Failed"
            elif pdf.get("conversion_started_at") and not is_converted:
                conversion_status = "🔄 Converting"
            
            df_data.append({
                "ID": pdf.get("id", ""),
                "URI": pdf.get("uri", "")[:50] + "..." if len(pdf.get("uri", "")) > 50 else pdf.get("uri", ""),
                "Filename": pdf.get("filename", ""),
                "File Size (KB)": round(pdf.get("file_size", 0) / 1024, 2) if pdf.get("file_size") else 0,
                "Status": "✅ Success" if pdf.get("status") == "success" else "❌ Error",
                "Downloaded": "✅ Yes" if pdf.get("is_downloaded") else "❌ No",
                "Converted": conversion_status,
                "Processed At": pdf.get("processed_at", "")[:19] if pdf.get("processed_at") else ""
            })
        
        df = pd.DataFrame(df_data)
        
        # Display the dataframe
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "URI": st.column_config.TextColumn("URI", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Downloaded": st.column_config.TextColumn("Downloaded", width="small"),
                "Converted": st.column_config.TextColumn("Converted", width="medium"),
            }
        )
        
        # Show detailed view for selected PDF
        st.subheader("PDF Details")
        selected_indices = st.selectbox(
            "Select a PDF to view details:",
            options=range(len(pdfs)),
            format_func=lambda i: f"{pdfs[i].get('filename', 'Unknown')} - {pdfs[i].get('uri', '')[:30]}..."
        )
        
        if selected_indices is not None:
            selected_pdf = pdfs[selected_indices]
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**ID:**", selected_pdf.get("id"))
                st.write("**Filename:**", selected_pdf.get("filename"))
                st.write("**File Size:**", f"{selected_pdf.get('file_size', 0):,} bytes")
                st.write("**Content Type:**", selected_pdf.get("content_type"))
                st.write("**Status:**", selected_pdf.get("status"))
                st.write("**Downloaded:**", "Yes" if selected_pdf.get("is_downloaded") else "No")
                
            with col2:
                st.write("**Converted:**", "✅ Yes" if selected_pdf.get("is_converted") else "❌ No")
                st.write("**Processed At:**", selected_pdf.get("processed_at"))
                
                # Conversion details
                if selected_pdf.get("conversion_started_at"):
                    st.write("**Conversion Started:**", selected_pdf.get("conversion_started_at")[:19])
                if selected_pdf.get("conversion_completed_at"):
                    st.write("**Conversion Completed:**", selected_pdf.get("conversion_completed_at")[:19])
                if selected_pdf.get("conversion_error"):
                    st.write("**Conversion Error:**", selected_pdf.get("conversion_error"))
                if selected_pdf.get("text_file_path"):
                    st.write("**Text File:**", selected_pdf.get("text_file_path"))
                if selected_pdf.get("images_folder_path"):
                    st.write("**Images Folder:**", selected_pdf.get("images_folder_path"))
                
                if selected_pdf.get("error_message"):
                    st.write("**Error:**", selected_pdf.get("error_message"))
            
            st.write("**Full URI:**", selected_pdf.get("uri"))
            st.write("**File Path:**", selected_pdf.get("file_path"))
            
            # Add manual conversion trigger button
            if (selected_pdf.get("is_downloaded") and 
                selected_pdf.get("status") == "success" and 
                not selected_pdf.get("is_converted") and 
                not selected_pdf.get("conversion_error")):
                
                st.markdown("---")
                if st.button("🔄 Trigger Conversion", key=f"convert_{selected_pdf.get('id')}"):
                    with st.spinner("Triggering conversion..."):
                        response = trigger_conversion(selected_pdf.get("uri"))
                        if response and response.status_code == 200:
                            st.success("Conversion triggered successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to trigger conversion")
            
            # Add delete section with confirmation
            st.markdown("---")
            st.subheader("🗑 Danger Zone")
            
            # Initialize session state for delete confirmation
            delete_key = f"confirm_delete_{selected_pdf.get('id')}"
            if delete_key not in st.session_state:
                st.session_state[delete_key] = False
            
            if not st.session_state[delete_key]:
                if st.button("🗑 Delete PDF", key=f"delete_{selected_pdf.get('id')}", type="secondary"):
                    st.session_state[delete_key] = True
                    st.rerun()
            else:
                # Build list of files that will be deleted
                files_to_delete = []
                if selected_pdf.get("file_path"):
                    files_to_delete.append("📄 Original PDF file")
                if selected_pdf.get("text_file_path"):
                    files_to_delete.append("📝 Extracted text file")
                if selected_pdf.get("images_folder_path"):
                    files_to_delete.append("🖼️ Extracted images folder")
                
                file_list = "\n• ".join(files_to_delete) if files_to_delete else "No files to delete"
                
                st.warning(f"""⚠️ **Are you sure you want to delete this PDF?**
                
**Filename:** {selected_pdf.get('filename')}
**File Size:** {selected_pdf.get('file_size', 0):,} bytes

**The following will be permanently deleted:**
• {file_list}
• Database record

**This action cannot be undone!**""")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Yes, Delete", key=f"confirm_yes_{selected_pdf.get('id')}", type="primary"):
                        with st.spinner("Deleting PDF..."):
                            response = delete_pdf(selected_pdf.get("uri"))
                            if response and response.status_code == 200:
                                st.success("PDF deleted successfully!")
                                # Reset session state
                                st.session_state[delete_key] = False
                                st.rerun()
                            else:
                                st.error("Failed to delete PDF")
                                st.session_state[delete_key] = False
                
                with col2:
                    if st.button("❌ Cancel", key=f"confirm_no_{selected_pdf.get('id')}"):
                        st.session_state[delete_key] = False
                        st.rerun()
            
    else:
        st.info("No PDFs have been processed yet. Use the 'Process New PDF' page to add some!")

elif page == "➕ Process New PDF":
    st.header("Process New PDF")
    
    user_input = st.text_input("Enter PDF URL:", placeholder="https://example.com/document.pdf")
    
    if st.button("Process PDF"):
        if user_input:
            with st.spinner("Processing PDF..."):
                try:
                    response = requests.post(f"{API_BASE_URL}/pdfs", json={"uri": user_input})
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success("PDF processed successfully!")
                        
                        # Show processing results
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Status:**", "✅ Success" if result.get("is_pdf") else "❌ Not a PDF")
                            st.write("**Downloaded:**", "✅ Yes" if result.get("downloaded") else "❌ No")
                            st.write("**From Cache:**", "Yes" if result.get("from_cache") else "No")
                        
                        with col2:
                            st.write("**Converted:**", "✅ Yes" if result.get("is_converted") else "⏳ Queued")
                            st.write("**Conversion Status:**", result.get("conversion_status", "Unknown"))
                            if result.get("file_size"):
                                st.write("**File Size:**", f"{result.get('file_size'):,} bytes")
                            if result.get("file_path"):
                                st.write("**Saved to:**", result.get("file_path"))
                        
                        st.write("**Message:**", result.get("message"))
                        
                        # Show conversion info if available
                        if result.get("conversion_status") == "queued":
                            st.info("🔄 PDF has been queued for conversion. Check back in a few minutes!")
                        
                    else:
                        st.error(f"Error: {response.status_code} - {response.text}")
                        
                except requests.exceptions.RequestException as e:
                    st.error(f"Connection error: {str(e)}")
        else:
            st.warning("Please enter a PDF URL")

elif page == "📊 Statistics":
    st.header("Processing Statistics")
    
    stats = get_stats()
    
    if stats:
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Processed", stats.get("total_processed", 0))
        
        with col2:
            st.metric("Successful Downloads", stats.get("successful_downloads", 0))
        
        with col3:
            st.metric("Converted PDFs", stats.get("converted_pdfs", 0))
        
        with col4:
            st.metric("Pending Conversion", stats.get("pending_conversion", 0))
        
        with col5:
            st.metric("Failed Attempts", stats.get("failed_attempts", 0))
        
        # File size metric
        col1, col2 = st.columns(2)
        with col1:
            total_size_mb = stats.get("total_file_size_bytes", 0) / (1024 * 1024)
            st.metric("Total Size (MB)", f"{total_size_mb:.2f}")
        
        # Success rate
        total = stats.get("total_processed", 0)
        successful = stats.get("successful_downloads", 0)
        if total > 0:
            success_rate = (successful / total) * 100
            with col2:
                st.metric("Download Success Rate", f"{success_rate:.1f}%")
        
        # Conversion rate
        downloaded = stats.get("successful_downloads", 0)
        converted = stats.get("converted_pdfs", 0)
        if downloaded > 0:
            conversion_rate = (converted / downloaded) * 100
            st.metric("Conversion Rate", f"{conversion_rate:.1f}%")
            
            # Progress bars
            st.subheader("Progress Overview")
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Download Success Rate**")
                st.progress(success_rate / 100 if total > 0 else 0)
            with col2:
                st.write("**Conversion Rate**")
                st.progress(conversion_rate / 100)
    else:
        st.error("Unable to fetch statistics")

elif page == "🔄 Conversion Queue":
    st.header("Conversion Queue Management")
    
    # Process conversion queue button
    if st.button("🚀 Process All Pending Conversions"):
        with st.spinner("Processing conversion queue..."):
            try:
                response = requests.post(f"{API_BASE_URL}/convert/process-queue")
                if response.status_code == 200:
                    result = response.json()
                    st.success(result.get("message", "Queue processed successfully!"))
                    
                    # Show results if available
                    if result.get("results"):
                        st.subheader("Conversion Results")
                        for res in result["results"]:
                            if res.get("success"):
                                st.success(f"✅ {res.get('uri')}: {res.get('message')}")
                            else:
                                st.error(f"❌ {res.get('uri')}: {res.get('error')}")
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Connection error: {str(e)}")
    
    st.markdown("---")
    st.info("Use this page to manually trigger conversion of all pending PDFs. The system automatically converts PDFs when they are first added, but you can use this if any conversions failed or were missed.")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**PDF Processor Dashboard**")
st.sidebar.markdown("Built with Streamlit & FastAPI")
st.sidebar.markdown("✨ Now with PDF Conversion!")
