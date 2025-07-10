import React, { useEffect, useState } from "react";
import {
    Box,
    Heading,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    Spinner,
    Text,
    Button,
    Center,
    useToast,
    useColorModeValue,
} from "@chakra-ui/react";

function SessionManager() {
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);
    const toast = useToast();
    const tableBg = useColorModeValue("white", "gray.800");

    const fetchSessions = () => {
        setLoading(true);
        fetch("/datacenter/session/status")
            .then((res) => res.json())
            .then((data) => {
                setSessions(data.active_sessions || []);
                setLoading(false);
            })
            .catch((err) => {
                console.error("Session check failed:", err);
                setSessions([]);
                setLoading(false);
            });
    };

    useEffect(() => {
        fetchSessions();
    }, []);

    const handleLogout = async (userId , Ip) => {
        const res = await fetch("/datacenter/logout", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: userId , ip:Ip }),
        });

        if (res.ok) {
            toast({
                title: `User ${userId} logged out.`,
                status: "success",
                duration: 3000,
                isClosable: true,
            });
            fetchSessions(); // 重新載入列表
        } else {
            toast({
                title: `Failed to log out ${userId}.`,
                status: "error",
                duration: 3000,
                isClosable: true,
            });
        }
    };

    return (
        <Box maxW="1000px" mx="auto" mt={10} p={6} bg={tableBg} rounded="md" boxShadow="md">
            <Heading mb={6} textAlign="center">Session Manager</Heading>

            {loading ? (
                <Center>
                    <Spinner size="xl" thickness="4px" speed="0.65s" color="teal.500" />
                </Center>
            ) : sessions.length > 0 ? (
                <Table variant="simple" size="md">
                    <Thead bg="teal.500">
                        <Tr>
                            <Th color="white">User ID</Th>
                            <Th color="white">Source IP</Th>
                            <Th color="white">ID Token (Preview)</Th>
                            <Th color="white">Login Time</Th>
                            <Th color="white">Action</Th>
                        </Tr>
                    </Thead>
                    <Tbody>
                        {sessions.map((s, index) => (
                            <Tr key={index}>
                                <Td>{s.user_id}</Td>
                                <Td>{s.ip}</Td>
                                <Td fontSize="sm" wordBreak="break-word">
                                    {s.id_token?.substring(0, 30)}...
                                </Td>
                                <Td>{s.login_time}</Td>
                                <Td>
                                    <Button
                                        colorScheme="red"
                                        size="sm"
                                        onClick={() => handleLogout(s.user_id, s.ip)}
                                    >
                                        Logout
                                    </Button>
                                </Td>
                            </Tr>
                        ))}
                    </Tbody>
                </Table>
            ) : (
                <Text textAlign="center" color="gray.500">
                    No active sessions found.
                </Text>
            )}
        </Box>
    );
}

export default SessionManager;
