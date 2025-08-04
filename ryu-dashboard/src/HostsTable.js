import React, { useEffect, useState } from "react";
import "./HostsTable.css";
import IntentTable from "./IntentTable";
import { Heading, Stack } from "@chakra-ui/react";

function HostsTable() {
  const [hosts, setHosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [labels, setLabels] = useState({
    function: [],
    priority: [],
    type: [],
    application: [],
    environment: [],
  });
  const [selectedLabels, setSelectedLabels] = useState({});
  const [epgDefaults, setEpgDefaults] = useState({});

  const API_URL_HOSTS = "http://sdn.yuntech.poc.com/ryu/hosts";
  const API_URL_LABEL = "http://sdn.yuntech.poc.com/datacenter/label/";
  const labelCategories = ["function", "priority", "type", "application", "environment","security"];

  useEffect(() => {
    fetch(API_URL_HOSTS)
      .then((response) => response.json())
      .then((data) => {
        setHosts(data);
        setLoading(false);
      })
      .catch((error) => {
        console.error("Error fetching hosts data:", error);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    labelCategories.forEach((category) => {
      fetch(API_URL_LABEL + category)
        .then((response) => response.json())
        .then((data) => {
          setLabels((prev) => ({
            ...prev,
            [category]: data,
          }));
        })
        .catch((error) => {
          console.error(`Error fetching ${category} labels:`, error);
        });
    });
  }, []);

  useEffect(() => {
    if (hosts.length === 0) return;
  
    const fetchEPGLabels = async () => {
      const newDefaults = {};
  
      for (const host of hosts) {
        const ip = host.ipv4?.[0];
        if (!ip) continue;
  
        try {
          const response = await fetch(`http://sdn.yuntech.poc.com/datacenter/epg/${ip}`);
          const data = await response.json();
          newDefaults[host.mac] = data;
        } catch (err) {
          console.error(`無法取得 ${ip} 的預設 EPG 標籤:`, err);
        }
      }
  
      setEpgDefaults(newDefaults);
    };
  
    fetchEPGLabels();
  }, [hosts]);
  

  const handleLabelChange = (event, mac, category) => {
    const { value } = event.target;
    setSelectedLabels((prev) => ({
      ...prev,
      [mac]: {
        ...prev[mac],
        [category]: value,
      },
    }));
  };

  const handleSubmit = (host) => {
    const labelsForHost = selectedLabels[host.mac] || {};

    const payload = {
      hostInfo: host,
      labels: labelsForHost,
    };
    console.log(payload)
    fetch("http://sdn.yuntech.poc.com/datacenter/submit_labels", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("Server response:", data);
        alert("Labels successfully submitted!");
      })
      .catch((error) => {
        console.error("Error submitting labels:", error);
        alert("Error submitting labels!");
      });
  };

  return (
    <Stack align="center">
      <Heading> SDN Monitoring Dashboard </Heading>
      <Heading as="h3" size="lg" noOfLines={1}>
        Host Information
      </Heading>

      {loading ? (
        <p style={{ textAlign: "center" }}>載入中...</p>
      ) : (
        <table className="tableStyle">
          <thead>
            <tr className="headerRowStyle">
              <th className="tableHeaderStyle">MAC Address</th>
              <th className="tableHeaderStyle">IPv4 Address</th>
              <th className="tableHeaderStyle">IPv6 Address</th>
              <th className="tableHeaderStyle">NIC</th>
              {labelCategories.map((cat) => (
                <th key={cat} className="tableHeaderStyle">
                  {cat.charAt(0).toUpperCase() + cat.slice(1)}
                </th>
              ))}
              <th className="tableHeaderStyle">Send</th>
            </tr>
          </thead>
          <tbody>
            {hosts.map((host, index) => (
              <tr
                key={index}
                style={{
                  backgroundColor: index % 2 === 0 ? "#f9f9f9" : "#fff",
                }}
              >
                <td className="tableCellStyle" data-label="MAC Address">{host.mac}</td>
                <td className="tableCellStyle" data-label="IPv4 Address">
                  {host.ipv4.length > 0 ? host.ipv4.join(", ") : "N/A"}
                </td>
                <td className="tableCellStyle" data-label="IPv6 Address">
                  {host.ipv6.length > 0 ? host.ipv6.join(", ") : "N/A"}
                </td>
                <td className="tableCellStyle" data-label="Port">{host.port.name}</td>
                {labelCategories.map((category) => (
                  <td key={category} className="tableCellStyle" data-label={category.charAt(0).toUpperCase() + category.slice(1)}>
                    <select
                      value={
                        selectedLabels[host.mac]?.[category] ??
                        epgDefaults[host.mac]?.[category] ??
                        ""
                      }
                      onChange={(e) => handleLabelChange(e, host.mac, category)}
                      className="select-style"
                    >
                      <option value="">Select Label</option>
                      {labels[category]?.map((label, idx) => (
                        <option key={idx} value={label}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </td>
                ))}
                <td className="tableCellStyle" data-label="Send">
                  <button
                    onClick={() => handleSubmit(host)}
                    className="submit-button"
                  >
                    Send
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <IntentTable />
    </Stack>
  );
}

export default HostsTable;
